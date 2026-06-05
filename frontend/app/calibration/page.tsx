"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/app/app-shell";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  StatusBadge,
  statusTone,
} from "@/components/app/page-primitives";
import { useAuth } from "@/components/auth/auth-provider";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { Button } from "@/components/ui/button";
import { ApiError, getCalibrationSessions } from "@/lib/api";
import { cn } from "@/lib/cn";
import type { CalibrationAgentReview, CalibrationSession } from "@/lib/types";

type CalibrationTab = "overview" | "agents" | "code" | "transcript";

const TABS: Array<{ id: CalibrationTab; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "agents", label: "Agent Reviews" },
  { id: "code", label: "Final Code" },
  { id: "transcript", label: "AI Transcript" },
];

const TIER_LABELS: Record<CalibrationSession["tier"], string> = {
  strong: "Strong candidate",
  average: "Average candidate",
  weak: "Weak candidate",
};

function sanitizeDisplayText(value: string | null | undefined): string {
  if (!value) {
    return "";
  }
  return value
    .replace(
      /\b(OPENAI_API_KEY|GITHUB_TOKEN|GH_TOKEN|API_KEY|SECRET_KEY|DATABASE_URL|PASSWORD|ACCESS_TOKEN)\s*[:=]\s*["']?[^"'\s]+/gi,
      "[redacted secret]",
    )
    .replace(/\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9_]{20,})\b/g, "[redacted secret]")
    .replace(/Traceback \(most recent call last\):[\s\S]*?(?=\n\n|$)/gi, "Stack trace redacted.")
    .replace(/\bgpt-[a-z0-9_.-]+/gi, "[model]");
}

function recommendationLabel(value: string): string {
  return value
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function recommendationTone(value: string): string {
  const normalized = value.toLowerCase().replace(/[_-]+/g, " ");
  if (normalized === "strong hire") {
    return "border-emerald-800 bg-emerald-950/60 text-emerald-100";
  }
  if (normalized === "hire") {
    return "border-cyan-800 bg-cyan-950/60 text-cyan-100";
  }
  if (normalized === "lean hire") {
    return "border-sky-800 bg-sky-950/60 text-sky-100";
  }
  if (normalized === "lean no hire") {
    return "border-amber-800 bg-amber-950/60 text-amber-100";
  }
  if (normalized === "no hire") {
    return "border-rose-800 bg-rose-950/60 text-rose-100";
  }
  return "border-slate-700 bg-slate-900 text-slate-200";
}

function scoreTone(score: number): string {
  if (score >= 80) {
    return "border-emerald-900/70 bg-emerald-950/30 text-emerald-200";
  }
  if (score >= 65) {
    return "border-cyan-900/70 bg-cyan-950/30 text-cyan-200";
  }
  if (score >= 50) {
    return "border-amber-900/70 bg-amber-950/30 text-amber-200";
  }
  return "border-rose-900/70 bg-rose-950/30 text-rose-200";
}

function tierTone(tier: CalibrationSession["tier"]): string {
  if (tier === "strong") {
    return "border-emerald-900/70 bg-emerald-950/20 text-emerald-200";
  }
  if (tier === "average") {
    return "border-cyan-900/70 bg-cyan-950/20 text-cyan-200";
  }
  return "border-rose-900/70 bg-rose-950/20 text-rose-200";
}

function RecommendationBadge({ recommendation }: { recommendation: string }) {
  return (
    <span className={cn("inline-flex h-8 items-center rounded-md border px-3 text-sm font-semibold", recommendationTone(recommendation))}>
      {recommendationLabel(recommendation)}
    </span>
  );
}

function SectionPanel({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-md border border-slate-800 bg-slate-900/70 p-5">
      <h2 className="text-lg font-semibold text-slate-50">{title}</h2>
      {description ? <p className="mt-1 text-sm leading-6 text-slate-400">{description}</p> : null}
      <div className="mt-5">{children}</div>
    </section>
  );
}

function TextList({ items, title }: { items: string[]; title: string }) {
  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</h3>
      <ul className="mt-2 grid gap-2 text-sm leading-6 text-slate-300">
        {items.map((item) => (
          <li className="rounded-md border border-slate-800 bg-slate-950/70 px-3 py-2" key={item}>
            {sanitizeDisplayText(item)}
          </li>
        ))}
      </ul>
    </div>
  );
}

function CalibrationSelector({
  sessions,
  selectedId,
  onSelect,
}: {
  sessions: CalibrationSession[];
  selectedId: string | null;
  onSelect: (sessionId: string) => void;
}) {
  return (
    <section className="grid gap-3 lg:grid-cols-3" aria-label="Calibration examples">
      {sessions.map((session) => {
        const isSelected = selectedId === session.id;
        return (
          <button
            aria-pressed={isSelected}
            className={cn(
              "rounded-md border p-4 text-left outline-none transition focus-visible:ring-2 focus-visible:ring-cyan-400/60",
              isSelected ? "border-cyan-500 bg-slate-900" : "border-slate-800 bg-slate-900/60 hover:border-slate-600",
            )}
            key={session.id}
            onClick={() => onSelect(session.id)}
            type="button"
          >
            <div className="flex items-start justify-between gap-3">
              <span className={cn("rounded-md border px-2.5 py-1 text-xs font-semibold", tierTone(session.tier))}>
                {TIER_LABELS[session.tier]}
              </span>
              <span className={cn("rounded-md border px-2.5 py-1 text-sm font-semibold", scoreTone(session.final_score))}>
                {session.final_score}
              </span>
            </div>
            <h2 className="mt-4 text-base font-semibold text-slate-100">{session.candidate_name}</h2>
            <p className="mt-1 text-sm text-slate-400">{session.scenario_title}</p>
            <div className="mt-3">
              <RecommendationBadge recommendation={session.recommendation} />
            </div>
          </button>
        );
      })}
    </section>
  );
}

function OverviewTab({ session }: { session: CalibrationSession }) {
  return (
    <div className="grid gap-5">
      <div className="grid gap-5 xl:grid-cols-[360px_minmax(0,1fr)]">
        <section className="rounded-md border border-slate-800 bg-slate-900/70 p-5">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Final recommendation</p>
          <div className="mt-3">
            <RecommendationBadge recommendation={session.recommendation} />
          </div>
          <p className="mt-4 text-5xl font-semibold text-slate-50">{session.final_score}</p>
          <p className="mt-2 text-sm leading-6 text-slate-400">{sanitizeDisplayText(session.review_summary)}</p>
        </section>

        <section className="rounded-md border border-slate-800 bg-slate-900/70 p-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-sm font-medium text-cyan-200">{session.role_title}</p>
              <h2 className="mt-1 text-xl font-semibold text-slate-50">{session.scenario_title}</h2>
              <p className="mt-2 text-sm text-slate-400">{session.candidate_name}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <StatusBadge label={session.status} tone={statusTone(session.status)} />
              <StatusBadge label={session.ai_mode} tone="info" />
            </div>
          </div>
          <div className="mt-5 rounded-md border border-slate-800 bg-slate-950/70 p-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h3 className="text-sm font-semibold text-slate-100">Validation result</h3>
                <p className="mt-1 text-sm text-slate-400">{sanitizeDisplayText(session.test_result.summary)}</p>
              </div>
              <StatusBadge
                label={`${session.test_result.passed_count}/${session.test_result.passed_count + session.test_result.failed_count} passed`}
                tone={session.test_result.status === "passed" ? "success" : "danger"}
              />
            </div>
            <pre className="mt-4 max-h-52 overflow-auto rounded-md border border-slate-800 bg-slate-950 p-3 text-xs leading-5 text-slate-300">
              {sanitizeDisplayText(session.test_result.output)}
            </pre>
          </div>
        </section>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <SectionPanel title="Expected Behavior">
          <TextList items={session.expected_behavior} title="What the task expected" />
        </SectionPanel>
        <SectionPanel title="Observed Behavior">
          <TextList items={session.observed_behavior} title="What the candidate did" />
        </SectionPanel>
      </div>

      <SectionPanel
        description="These are the review signals that make the calibration examples useful when comparing real submissions."
        title="What Separated This Performance"
      >
        <TextList items={session.differentiators} title="Key differentiators" />
      </SectionPanel>
    </div>
  );
}

function AgentReviewCard({ review }: { review: CalibrationAgentReview }) {
  return (
    <article className="grid gap-4 rounded-md border border-slate-800 bg-slate-900/70 p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{review.agent_type.replace(/_/g, " ")}</p>
          <h3 className="mt-1 text-base font-semibold text-slate-100">{review.agent_label}</h3>
          <p className="mt-2 text-sm leading-6 text-slate-400">{sanitizeDisplayText(review.summary)}</p>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          <RecommendationBadge recommendation={review.recommendation} />
          <span className={cn("rounded-md border px-3 py-1 text-sm font-semibold", scoreTone(review.score))}>
            Score {review.score}
          </span>
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <TextList items={review.strengths} title="Strengths" />
        <TextList items={review.weaknesses} title="Weaknesses" />
        <TextList items={review.evidence} title="Evidence" />
        <TextList items={review.risk_flags.length ? review.risk_flags : ["No material risk flags recorded."]} title="Risk Flags" />
      </div>
    </article>
  );
}

function AgentsTab({ session }: { session: CalibrationSession }) {
  return (
    <div className="grid gap-4">
      {session.agent_reviews.map((review) => (
        <AgentReviewCard key={review.agent_type} review={review} />
      ))}
    </div>
  );
}

function CodeTab({ session }: { session: CalibrationSession }) {
  return (
    <SectionPanel
      description="Final submitted code from the calibration example."
      title="Final Code"
    >
      <div className="rounded-md border border-slate-800 bg-slate-950">
        <div className="flex flex-col gap-2 border-b border-slate-800 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="font-mono text-sm text-cyan-100">{session.final_code_path}</p>
          <span className="text-xs uppercase tracking-wide text-slate-500">{session.final_code_language}</span>
        </div>
        <pre className="max-h-[36rem] overflow-auto p-4 text-xs leading-5 text-slate-200">
          {sanitizeDisplayText(session.final_code)}
        </pre>
      </div>
    </SectionPanel>
  );
}

function TranscriptTab({ session }: { session: CalibrationSession }) {
  return (
    <SectionPanel
      description="Candidate prompts and AI responses used during this completed calibration session."
      title="AI Transcript"
    >
      <div className="grid gap-3">
        {session.ai_transcript.map((message, index) => {
          const isUser = message.role === "user";
          return (
            <article
              className={cn(
                "rounded-md border p-4",
                isUser ? "border-cyan-900/70 bg-cyan-950/20" : "border-slate-800 bg-slate-950",
              )}
              key={`${message.role}-${index}`}
            >
              <span
                className={cn(
                  "rounded-full border px-3 py-1 text-xs font-medium",
                  isUser ? "border-cyan-800 text-cyan-100" : "border-slate-700 text-slate-300",
                )}
              >
                {isUser ? "Candidate" : "AI Copilot"}
              </span>
              <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-300">{sanitizeDisplayText(message.content)}</p>
            </article>
          );
        })}
      </div>
    </SectionPanel>
  );
}

function TabBar({
  activeTab,
  onTabChange,
}: {
  activeTab: CalibrationTab;
  onTabChange: (tab: CalibrationTab) => void;
}) {
  return (
    <div className="overflow-x-auto border-b border-slate-800">
      <div className="flex min-w-max gap-1">
        {TABS.map((tab) => (
          <button
            className={cn(
              "h-11 rounded-t-md px-4 text-sm font-medium outline-none transition focus-visible:ring-2 focus-visible:ring-cyan-400/60",
              activeTab === tab.id
                ? "bg-slate-900 text-cyan-200"
                : "text-slate-400 hover:bg-slate-900/70 hover:text-slate-100",
            )}
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            type="button"
          >
            {tab.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function TabContent({ activeTab, session }: { activeTab: CalibrationTab; session: CalibrationSession }) {
  if (activeTab === "agents") {
    return <AgentsTab session={session} />;
  }
  if (activeTab === "code") {
    return <CodeTab session={session} />;
  }
  if (activeTab === "transcript") {
    return <TranscriptTab session={session} />;
  }
  return <OverviewTab session={session} />;
}

function CalibrationContent() {
  const { token, user } = useAuth();
  const [sessions, setSessions] = useState<CalibrationSession[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<CalibrationTab>("overview");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const canView = user?.role === "ADMIN" || user?.role === "INTERVIEWER";

  const loadCalibration = useCallback(async () => {
    if (!token || !canView) {
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const loadedSessions = await getCalibrationSessions(token);
      setSessions(loadedSessions);
      setSelectedId((currentId) => currentId ?? loadedSessions[0]?.id ?? null);
    } catch (requestError: unknown) {
      const message = requestError instanceof ApiError ? requestError.message : "Unable to load calibration examples.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [canView, token]);

  useEffect(() => {
    void loadCalibration();
  }, [loadCalibration]);

  const selectedSession = useMemo(
    () => sessions.find((session) => session.id === selectedId) ?? sessions[0] ?? null,
    [selectedId, sessions],
  );

  function handleSelect(sessionId: string) {
    setSelectedId(sessionId);
    setActiveTab("overview");
  }

  if (!canView) {
    return (
      <AppShell>
        <PageHeader
          description="Calibration examples are available only to interviewer and admin roles."
          eyebrow="Access"
          title="Calibration"
        />
        <div className="mt-6">
          <EmptyState description="Candidate accounts cannot inspect interviewer calibration examples." title="Calibration unavailable" />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <PageHeader
        actions={
          <Link
            className="inline-flex h-10 items-center justify-center rounded-md border border-slate-700 px-4 text-sm font-medium text-slate-200 transition hover:border-slate-500 hover:text-white"
            href="/results"
          >
            View real results
          </Link>
        }
        description="Compare strong, average, and weak completed submissions so interviewers can calibrate scoring expectations before reviewing real candidates."
        eyebrow="Interviewer calibration"
        title="Calibration"
      />

      <main className="mt-6 grid max-w-7xl gap-5">
        {isLoading ? <LoadingState label="Loading calibration examples" rows={4} /> : null}
        {error ? (
          <div className="grid gap-3">
            <ErrorState message={error} />
            <Button className="w-fit" onClick={() => void loadCalibration()} type="button" variant="secondary">
              Retry
            </Button>
          </div>
        ) : null}

        {!isLoading && !error && sessions.length === 0 ? (
          <EmptyState
            description="Calibration examples are not available yet. Check backend seed data and try again."
            title="No calibration examples"
          />
        ) : null}

        {sessions.length ? <CalibrationSelector onSelect={handleSelect} selectedId={selectedSession?.id ?? null} sessions={sessions} /> : null}

        {selectedSession ? (
          <section className="grid gap-5">
            <section className="rounded-md border border-slate-800 bg-slate-900/70 p-5">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={cn("rounded-md border px-2.5 py-1 text-xs font-semibold", tierTone(selectedSession.tier))}>
                      {TIER_LABELS[selectedSession.tier]}
                    </span>
                    <RecommendationBadge recommendation={selectedSession.recommendation} />
                  </div>
                  <h2 className="mt-4 text-2xl font-semibold text-slate-50">{selectedSession.scenario_title}</h2>
                  <p className="mt-2 text-sm leading-6 text-slate-400">
                    {selectedSession.role_title} / {selectedSession.candidate_name}
                  </p>
                </div>
                <div className={cn("w-fit rounded-md border px-4 py-3", scoreTone(selectedSession.final_score))}>
                  <p className="text-xs uppercase tracking-wide opacity-80">Overall score</p>
                  <p className="mt-1 text-2xl font-semibold">{selectedSession.final_score}</p>
                </div>
              </div>
            </section>

            <TabBar activeTab={activeTab} onTabChange={setActiveTab} />
            <TabContent activeTab={activeTab} session={selectedSession} />
          </section>
        ) : null}
      </main>
    </AppShell>
  );
}

export default function CalibrationPage() {
  return (
    <ProtectedRoute>
      <CalibrationContent />
    </ProtectedRoute>
  );
}
