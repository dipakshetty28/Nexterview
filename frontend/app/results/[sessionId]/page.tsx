"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { type ReactNode, useCallback, useEffect, useMemo, useState } from "react";
import ReactMarkdown, { type Components } from "react-markdown";

import { AppShell } from "@/components/app/app-shell";
import { CoachMark } from "@/components/app/coach-mark";
import {
  EmptyState,
  ErrorState,
  InfoTooltip,
  LoadingState,
  PageHeader,
  StatusBadge,
  formatDateTime,
  statusTone,
} from "@/components/app/page-primitives";
import { useAuth } from "@/components/auth/auth-provider";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { Button } from "@/components/ui/button";
import { ApiError, getInterview, getSessionResult, runSubmissionReview } from "@/lib/api";
import { cn } from "@/lib/cn";
import type {
  AgentReview,
  AITranscriptMessage,
  FileDiff,
  ScoreBreakdownItem,
  SessionResult,
  SubmittedCodeFile,
  TelemetryTimelineEvent,
} from "@/lib/types";

type ResultTab = "overview" | "agents" | "code" | "tests" | "transcript" | "timeline";

type TimelineGroup = {
  id: string;
  eventType: string;
  label: string;
  count: number;
  firstAt: string;
  lastAt: string;
  details: string[];
};

const RESULT_TABS: Array<{ id: ResultTab; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "agents", label: "Agent Reviews" },
  { id: "code", label: "Code" },
  { id: "tests", label: "Tests" },
  { id: "transcript", label: "AI Transcript" },
  { id: "timeline", label: "Timeline" },
];

const SCORE_LABELS: Record<string, string> = {
  code_quality: "Code Quality",
  correctness: "Correctness",
  architecture: "Architecture",
  debugging_process: "Debugging",
  ai_usage: "AI Usage",
  prompting_skill: "Prompting Skill",
  communication: "Communication",
};

const RECOMMENDATION_LABELS: Record<string, string> = {
  "strong hire": "Strong Hire",
  hire: "Hire",
  "lean hire": "Lean Hire",
  "lean no hire": "Lean No Hire",
  "no hire": "No Hire",
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
    .replace(/https?:\/\/(?:api\.)?github\.com\/[^\s)]+/gi, "[redacted link]")
    .replace(/Traceback \(most recent call last\):[\s\S]*?(?=\n\n|$)/gi, "Stack trace redacted.")
    .replace(/\bgpt-[a-z0-9_.-]+/gi, "[model]");
}

function normalizedRecommendation(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }
  return value.toLowerCase().replace(/[_-]+/g, " ").trim();
}

function recommendationLabel(value: string | null | undefined): string {
  const normalized = normalizedRecommendation(value);
  if (!normalized) {
    return "Pending Review";
  }
  return RECOMMENDATION_LABELS[normalized] ?? normalized.replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function recommendationTone(value: string | null | undefined): string {
  const normalized = normalizedRecommendation(value);
  if (normalized === "strong hire") {
    return "border-emerald-200 bg-emerald-50 text-emerald-700";
  }
  if (normalized === "hire") {
    return "border-blue-200 bg-blue-50 text-blue-700";
  }
  if (normalized === "lean hire") {
    return "border-sky-200 bg-sky-50 text-sky-700";
  }
  if (normalized === "lean no hire") {
    return "border-amber-200 bg-amber-50 text-amber-800";
  }
  if (normalized === "no hire") {
    return "border-rose-200 bg-rose-50 text-rose-700";
  }
  return "border-slate-200 bg-slate-100 text-slate-700";
}

function scoreTone(score: number | null | undefined): string {
  if (score === null || score === undefined) {
    return "border-slate-200 bg-slate-100 text-slate-600";
  }
  if (score >= 80) {
    return "border-emerald-200 bg-emerald-50 text-emerald-700";
  }
  if (score >= 65) {
    return "border-blue-200 bg-blue-50 text-blue-700";
  }
  if (score >= 50) {
    return "border-amber-200 bg-amber-50 text-amber-800";
  }
  return "border-rose-200 bg-rose-50 text-rose-700";
}

function scoreLabel(item: ScoreBreakdownItem): string {
  return SCORE_LABELS[item.agent_type] ?? item.label.replace(" Agent", "");
}

function scoreQuality(score: number | null | undefined): string {
  if (score === null || score === undefined) {
    return "Pending";
  }
  if (score >= 85) {
    return "Strong";
  }
  if (score >= 70) {
    return "Solid";
  }
  if (score >= 55) {
    return "Mixed";
  }
  return "Concern";
}

function conciseText(value: string | null | undefined, maxLength = 150): string {
  const normalized = sanitizeDisplayText(value)
    .replace(/[*_`#>]/g, "")
    .replace(/\s+/g, " ")
    .trim();
  if (!normalized) {
    return "";
  }
  return normalized.length > maxLength ? `${normalized.slice(0, maxLength - 1).trim()}...` : normalized;
}

function scoreReason(result: SessionResult, item: ScoreBreakdownItem): string {
  const review = result.agent_reviews.find((candidate) => candidate.agent_type === item.agent_type);
  return (
    conciseText(review?.observed[0]) ||
    conciseText(review?.evidence[0]) ||
    conciseText(review?.explanation) ||
    "Reviewer reasoning will appear when this dimension is complete."
  );
}

function formatDuration(durationMs: number): string {
  if (durationMs < 1000) {
    return `${durationMs} ms`;
  }
  return `${(durationMs / 1000).toFixed(durationMs >= 10000 ? 0 : 1)} s`;
}

function SectionPanel({
  title,
  description,
  aside,
  children,
}: {
  title: string;
  description?: string;
  aside?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="rounded-card border border-slate-200/80 bg-white/95 p-5 shadow-panel backdrop-blur">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-950">{title}</h2>
          {description ? <p className="mt-1 text-sm leading-6 text-slate-600">{description}</p> : null}
        </div>
        {aside ? <div className="shrink-0">{aside}</div> : null}
      </div>
      <div className="mt-5">{children}</div>
    </section>
  );
}

function RecommendationBadge({ recommendation }: { recommendation: string | null | undefined }) {
  return (
    <span className={cn("inline-flex h-8 items-center rounded-full border px-3 text-sm font-semibold", recommendationTone(recommendation))}>
      {recommendationLabel(recommendation)}
    </span>
  );
}

function MiniMetric({ label, value, description }: { label: string; value: string | number; description?: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50/85 p-3 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 text-xl font-semibold text-slate-950">{value}</p>
      {description ? <p className="mt-1 text-xs leading-5 text-slate-600">{description}</p> : null}
    </div>
  );
}

const markdownComponents: Components = {
  h1: ({ children }) => <h1 className="mb-3 mt-4 text-lg font-semibold text-slate-950 first:mt-0">{children}</h1>,
  h2: ({ children }) => <h2 className="mb-2 mt-4 text-base font-semibold text-slate-950 first:mt-0">{children}</h2>,
  h3: ({ children }) => <h3 className="mb-2 mt-3 text-sm font-semibold text-slate-900 first:mt-0">{children}</h3>,
  p: ({ children }) => <p className="my-2 leading-6 text-slate-700">{children}</p>,
  ul: ({ children }) => <ul className="my-2 ml-5 list-disc space-y-1 text-slate-700">{children}</ul>,
  ol: ({ children }) => <ol className="my-2 ml-5 list-decimal space-y-1 text-slate-700">{children}</ol>,
  li: ({ children }) => <li className="leading-6">{children}</li>,
  blockquote: ({ children }) => (
    <blockquote className="my-3 border-l-2 border-blue-300 pl-3 text-sm text-slate-700">{children}</blockquote>
  ),
  a: ({ children, href }) => (
    <a className="text-blue-700 underline-offset-4 hover:underline" href={href} rel="noreferrer" target="_blank">
      {children}
    </a>
  ),
  pre: ({ children }) => (
    <pre className="my-3 max-h-96 overflow-auto rounded-md border border-slate-800 bg-slate-950 p-3 text-xs leading-5 text-slate-200">
      {children}
    </pre>
  ),
  code: ({ children, className }) => {
    const isBlock = Boolean(className);
    return (
      <code
        className={cn(
          isBlock
            ? "block whitespace-pre font-mono text-xs text-slate-200"
            : "rounded border border-slate-200 bg-slate-100 px-1.5 py-0.5 font-mono text-[0.85em] text-blue-700",
        )}
      >
        {children}
      </code>
    );
  },
};

function MarkdownBlock({ content, emptyLabel }: { content: string | null | undefined; emptyLabel: string }) {
  const safeContent = sanitizeDisplayText(content);
  if (!safeContent.trim()) {
    return <p className="text-sm text-slate-500">{emptyLabel}</p>;
  }
  return (
    <div className="text-sm">
      <ReactMarkdown components={markdownComponents}>{safeContent}</ReactMarkdown>
    </div>
  );
}

function TextList({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</h4>
      <ul className="mt-2 grid gap-2 text-sm leading-6 text-slate-700">
        {items.length ? (
          items.map((item) => (
            <li className="flex gap-2" key={item}>
              <span aria-hidden="true" className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-slate-400" />
              <span>{sanitizeDisplayText(item)}</span>
            </li>
          ))
        ) : (
          <li className="text-slate-500">None recorded.</li>
        )}
      </ul>
    </div>
  );
}

function RiskFlagList({ flags }: { flags: string[] }) {
  if (!flags.length) {
    return <p className="text-sm text-slate-500">No cross-agent risk flags recorded.</p>;
  }
  return (
    <div className="flex flex-wrap gap-2">
      {flags.map((flag) => (
        <span className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-medium text-amber-800" key={flag}>
          {sanitizeDisplayText(flag)}
        </span>
      ))}
    </div>
  );
}

function DiffBlock({ diff }: { diff: FileDiff }) {
  return (
    <details className="rounded-md border border-slate-800 bg-slate-950">
      <summary className="cursor-pointer px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/60">
        <span className="font-medium text-slate-100">{diff.path}</span>
        <span className="ml-2 text-xs text-slate-500">
          {diff.status} / +{diff.additions} -{diff.deletions}
        </span>
      </summary>
      <pre className="max-h-96 overflow-auto border-t border-slate-800 p-3 text-xs leading-5 text-slate-200">
        {sanitizeDisplayText(diff.diff) || "No textual diff available."}
      </pre>
    </details>
  );
}

function CodeFileBlock({ file }: { file: SubmittedCodeFile }) {
  return (
    <details className="rounded-md border border-slate-800 bg-slate-950">
      <summary className="cursor-pointer px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/60">
        <span className="font-medium text-slate-100">{file.path}</span>
        <span className="ml-2 text-xs text-slate-500">
          {file.language}
          {file.file_type ? ` / ${file.file_type}` : ""}
        </span>
      </summary>
      <pre className="max-h-[34rem] overflow-auto border-t border-slate-800 p-3 text-xs leading-5 text-slate-200">
        {sanitizeDisplayText(file.content)}
      </pre>
    </details>
  );
}

function ScoreBreakdown({ result }: { result: SessionResult }) {
  return (
    <SectionPanel
      aside={
        <InfoTooltip
          content="Each dimension is backed by an independent reviewer. The overall score applies the configured evaluation weights."
          label="How scoring works"
        />
      }
      description="A decision-ready view of every weighted evaluation dimension and its evidence-based rationale."
      title="Score Breakdown"
    >
      {result.score_breakdown.length ? (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {result.score_breakdown.map((item) => (
            <article
              className="relative overflow-hidden rounded-lg border border-slate-200 bg-slate-50/80 p-4 shadow-sm"
              key={item.agent_type}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-slate-950">{scoreLabel(item)}</p>
                  <p className="mt-1 text-xs text-slate-500">Weight {item.weight}%</p>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-semibold tracking-tight text-slate-950">{item.score ?? "--"}</p>
                  <span className={cn("mt-1 inline-flex rounded-full border px-2 py-0.5 text-[11px] font-semibold", scoreTone(item.score))}>
                    {scoreQuality(item.score)}
                  </span>
                </div>
              </div>
              <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-slate-200">
                <div
                  className={cn(
                    "h-full rounded-full",
                    item.score === null
                      ? "bg-slate-300"
                      : item.score >= 80
                        ? "bg-emerald-500"
                        : item.score >= 65
                          ? "bg-blue-500"
                          : item.score >= 50
                            ? "bg-amber-500"
                            : "bg-rose-500",
                  )}
                  style={{ width: `${Math.max(0, Math.min(100, item.score ?? 0))}%` }}
                />
              </div>
              <p className="mt-3 text-sm leading-5 text-slate-600">{scoreReason(result, item)}</p>
            </article>
          ))}
        </div>
      ) : (
        <EmptyState description="Run the agent review to populate score dimensions." title="Score breakdown not ready" />
      )}
    </SectionPanel>
  );
}

function ExpectedObserved({ result }: { result: SessionResult }) {
  const evidence = Array.from(new Set(result.agent_reviews.flatMap((review) => review.evidence))).slice(0, 10);

  return (
    <SectionPanel
      description="The core comparison behind the recommendation, separated from reviewer opinion."
      title="Expected vs. Observed"
    >
      <CoachMark
        arrow="top"
        className="mb-4"
        description="Use this section to understand why the candidate received the score."
        id="results-expected-observed"
        title="Follow the evidence"
      />
      <div className="grid gap-3 lg:grid-cols-2">
        <article className="rounded-lg border border-blue-200 bg-blue-50/70 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-700">What was expected</p>
          <div className="mt-3">
            <TextList items={result.expected_behavior} title="Target behavior" />
          </div>
          {result.expected_solution_summary ? (
            <div className="mt-4 border-t border-blue-200 pt-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-blue-700">Intended approach</p>
              <MarkdownBlock content={result.expected_solution_summary} emptyLabel="No expected solution summary was stored." />
            </div>
          ) : null}
        </article>
        <article className="rounded-lg border border-emerald-200 bg-emerald-50/65 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">What the candidate did</p>
          <div className="mt-3">
            <TextList items={result.candidate_observed} title="Observed behavior" />
          </div>
        </article>
        <article className="rounded-lg border border-amber-200 bg-amber-50/70 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-amber-800">What was missing</p>
          <div className="mt-3">
            <TextList items={result.candidate_missed} title="Gaps and weaknesses" />
          </div>
        </article>
        <article className="rounded-lg border border-slate-200 bg-slate-50/90 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">Supporting evidence</p>
          <div className="mt-3">
            <TextList items={evidence} title="Recorded signals" />
          </div>
        </article>
      </div>
      <details className="mt-4 rounded-lg border border-slate-200 bg-white">
        <summary className="cursor-pointer px-4 py-3 text-sm font-semibold text-slate-800">
          Interviewer-only evaluation context
        </summary>
        <div className="grid gap-4 border-t border-slate-200 p-4 md:grid-cols-2">
          <TextList items={result.hidden_evaluation_points} title="Hidden Evaluation Points" />
          <TextList items={result.interviewer_rubric} title="Interviewer Rubric" />
        </div>
      </details>
    </SectionPanel>
  );
}

function AIUsageSummary({ result }: { result: SessionResult }) {
  const blindCopySignals = result.risk_flags.filter((flag) => /blind|copy|paste|unvalidated|ai/i.test(flag));
  return (
    <SectionPanel
      title="AI Usage Report"
    >
      <CoachMark
        arrow="top"
        className="mb-4"
        description="This score reflects prompt specificity, validation behavior, and independence."
        id="results-ai-usage"
        title="AI usage is a signal"
      />
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div>
          <MarkdownBlock content={result.ai_usage_analysis.summary} emptyLabel="No AI usage summary is available." />
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <TextList items={result.prompt_quality_summary.strengths} title="Strong Prompt Signals" />
            <TextList items={result.prompt_quality_summary.risks} title="Weak Prompt Signals" />
          </div>
          {blindCopySignals.length ? (
            <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3">
              <TextList items={blindCopySignals} title="Copy-Paste / Validation Risks" />
            </div>
          ) : null}
        </div>
        <div className="grid grid-cols-2 gap-3">
          <MiniMetric label="Prompts" value={result.ai_usage_analysis.candidate_prompt_count} />
          <MiniMetric label="AI Responses" value={result.ai_usage_analysis.assistant_response_count} />
          <MiniMetric label="With File Context" value={result.ai_usage_analysis.prompts_with_file_context} />
          <MiniMetric label="Validation Prompts" value={result.prompt_quality_summary.validation_prompt_count} />
          <MiniMetric label="Vague Prompts" value={result.prompt_quality_summary.vague_prompt_count} />
          <MiniMetric
            label="Validated AI Output"
            value={result.ai_usage_analysis.validated_suggestions ? "Evident" : "Not evident"}
          />
        </div>
      </div>
    </SectionPanel>
  );
}

function ResultOverview({ result }: { result: SessionResult }) {
  return (
    <div className="grid gap-5">
      <ExpectedObserved result={result} />
      <ScoreBreakdown result={result} />
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
        <SectionPanel title="Candidate Explanation">
          <MarkdownBlock content={result.notes} emptyLabel="No final explanation was submitted." />
        </SectionPanel>
        <SectionPanel title="Decision Risks">
          <RiskFlagList flags={result.risk_flags} />
        </SectionPanel>
      </div>
      <AIUsageSummary result={result} />
    </div>
  );
}

function AgentReviewCard({ review }: { review: AgentReview }) {
  return (
    <details className="group overflow-hidden rounded-card border border-slate-200/80 bg-white/95 shadow-panel" open={false}>
      <summary className="cursor-pointer list-none p-5">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {review.agent_type.replace(/_/g, " ")}
              </p>
              {review.confidence !== null && review.confidence !== undefined ? (
                <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] font-medium text-slate-600">
                  {Math.round(review.confidence * 100)}% confidence
                </span>
              ) : null}
            </div>
            <h3 className="mt-1 text-lg font-semibold text-slate-950">{review.agent_label}</h3>
            <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-600">
              {conciseText(review.explanation, 220) || "No reviewer explanation was recorded."}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-3">
            <RecommendationBadge recommendation={review.recommendation} />
            <span className={cn("rounded-full border px-3 py-1 text-sm font-semibold", scoreTone(review.score))}>
              {review.score}
            </span>
            <span
              aria-hidden="true"
              className="text-lg text-slate-400 transition group-open:rotate-180"
            >
              v
            </span>
          </div>
        </div>
      </summary>
      <div className="border-t border-slate-200 bg-slate-50/60 p-5">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Review summary</p>
          <MarkdownBlock content={review.explanation} emptyLabel="No reviewer explanation was recorded." />
        </div>
        <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <div className="rounded-lg border border-blue-200 bg-blue-50/60 p-4">
            <TextList items={review.expected} title="Expected" />
          </div>
          <div className="rounded-lg border border-emerald-200 bg-emerald-50/60 p-4">
            <TextList items={review.observed} title="Observed" />
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <TextList items={review.evidence} title="Evidence" />
          </div>
          <div className="rounded-lg border border-emerald-200 bg-emerald-50/60 p-4">
            <TextList items={review.strengths} title="Strengths" />
          </div>
          <div className="rounded-lg border border-amber-200 bg-amber-50/60 p-4">
            <TextList items={review.weaknesses} title="Weaknesses" />
          </div>
          <div className="rounded-lg border border-rose-200 bg-rose-50/60 p-4">
            <TextList items={review.risk_flags} title="Risk Flags" />
          </div>
        </div>
        <div className="mt-4 rounded-lg border border-violet-200 bg-violet-50/60 p-4">
          <TextList items={review.follow_up_questions} title="Suggested Follow-Up Questions" />
        </div>
      </div>
    </details>
  );
}

function AgentReviews({ result }: { result: SessionResult }) {
  return (
    <div className="grid gap-4">
      {result.agent_reviews.length ? (
        <>
          <div className="px-1">
            <h2 className="text-xl font-semibold text-slate-950">Independent Agent Reviews</h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">
              Open any reviewer to inspect expected behavior, observed evidence, risks, and targeted follow-up questions.
            </p>
          </div>
          <div className="grid gap-3">
            {result.agent_reviews.map((review) => <AgentReviewCard key={review.id} review={review} />)}
          </div>
        </>
      ) : (
        <EmptyState description="The submission is saved, but agent review output is not ready yet." title="Review still running" />
      )}
    </div>
  );
}

function CodeSubmission({ result }: { result: SessionResult }) {
  return (
    <div className="grid gap-5">
      <SectionPanel title="Candidate Explanation">
        <MarkdownBlock content={result.notes} emptyLabel="No final explanation was submitted." />
      </SectionPanel>

      <SectionPanel
        aside={<span className="text-xs uppercase tracking-wide text-slate-500">{result.changed_files.length} files</span>}
        title="Changed Files"
      >
        <div className="flex flex-wrap gap-2">
          {result.changed_files.length ? (
            result.changed_files.map((path) => (
              <span className="rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs text-blue-700" key={path}>
                {path}
              </span>
            ))
          ) : (
            <span className="text-sm text-slate-500">No changed files detected.</span>
          )}
        </div>
      </SectionPanel>

      <SectionPanel
        aside={<span className="text-xs uppercase tracking-wide text-slate-500">{result.file_diffs.length} diffs</span>}
        title="File Diffs"
      >
        <div className="grid gap-3">
          {result.file_diffs.length ? (
            result.file_diffs.map((diff) => <DiffBlock diff={diff} key={diff.path} />)
          ) : (
            <p className="text-sm text-slate-500">No textual diffs were stored.</p>
          )}
        </div>
      </SectionPanel>

      <SectionPanel
        aside={<span className="text-xs uppercase tracking-wide text-slate-500">{result.submitted_files.length} files</span>}
        title="Submitted Code"
      >
        <div className="grid gap-3">
          {result.submitted_files.length ? (
            result.submitted_files.map((file) => <CodeFileBlock file={file} key={file.path} />)
          ) : (
            <p className="text-sm text-slate-500">No submitted files were stored.</p>
          )}
        </div>
      </SectionPanel>
    </div>
  );
}

function TestReport({ result }: { result: SessionResult }) {
  const firstRun = result.test_runs[0];
  const finalRun = result.test_runs[result.test_runs.length - 1];
  const validationCommand = finalRun?.command ?? firstRun?.command ?? "";

  return (
    <div className="grid gap-5">
      <SectionPanel
        aside={
          finalRun ? (
            <StatusBadge label={finalRun.status} tone={finalRun.status === "passed" ? "success" : statusTone(finalRun.status)} />
          ) : null
        }
        description="Stored validation attempts from the candidate workspace, shown in execution order."
        title="Test Validation Summary"
      >
        {result.test_runs.length ? (
          <>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <MiniMetric label="Final Status" value={finalRun?.status ?? "Not run"} />
              <MiniMetric label="First Run" value={firstRun?.status ?? "Not run"} />
              <MiniMetric label="Attempts" value={result.test_runs.length} />
              <MiniMetric
                label="Final Pass Count"
                value={finalRun ? `${finalRun.passed_count}/${finalRun.total_count}` : "--"}
              />
            </div>
            {validationCommand ? (
              <div className="mt-4 rounded-lg border border-slate-800 bg-slate-950 px-4 py-3 text-slate-100">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Validation command</p>
                <code className="mt-2 block overflow-x-auto font-mono text-sm text-cyan-200">
                  {sanitizeDisplayText(validationCommand)}
                </code>
              </div>
            ) : null}
            {finalRun?.failure_summary ? (
              <div className="mt-4 rounded-lg border border-rose-200 bg-rose-50 p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-rose-700">Final failure summary</p>
                <p className="mt-2 text-sm leading-6 text-rose-800">{sanitizeDisplayText(finalRun.failure_summary)}</p>
              </div>
            ) : null}
          </>
        ) : (
          <EmptyState
            description="No validation attempts were recorded for this candidate session."
            embedded
            title="No test runs"
          />
        )}
      </SectionPanel>

      {result.test_runs.length ? (
        <section className="overflow-hidden rounded-card border border-slate-200/80 bg-white/95 shadow-panel">
          <div className="border-b border-slate-200 px-5 py-4">
            <h2 className="text-lg font-semibold text-slate-950">Execution History</h2>
            <p className="mt-1 text-sm text-slate-600">Every stored test attempt, including duration and failure evidence.</p>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-5 py-3 font-medium">Attempt</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  <th className="px-5 py-3 font-medium">Pass / Fail</th>
                  <th className="px-5 py-3 font-medium">Duration</th>
                  <th className="px-5 py-3 font-medium">Run at</th>
                  <th className="px-5 py-3 font-medium">Summary</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {result.test_runs.map((run, index) => (
                  <tr className="transition hover:bg-sky-50/60" key={run.id}>
                    <td className="px-5 py-4 font-semibold text-slate-900">#{index + 1}</td>
                    <td className="px-5 py-4">
                      <StatusBadge label={run.status} tone={run.status === "passed" ? "success" : statusTone(run.status)} />
                    </td>
                    <td className="px-5 py-4 text-slate-700">
                      {run.passed_count} passed / {run.failed_count} failed
                    </td>
                    <td className="px-5 py-4 text-slate-600">{formatDuration(run.duration_ms)}</td>
                    <td className="px-5 py-4 text-slate-600">{formatDateTime(run.created_at)}</td>
                    <td className="max-w-md px-5 py-4 text-slate-600">
                      {sanitizeDisplayText(run.failure_summary) || "All recorded checks passed."}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      <SectionPanel title="Submitted Test Output">
        <pre className="max-h-[32rem] overflow-auto whitespace-pre-wrap rounded-lg border border-slate-800 bg-slate-950 p-4 text-sm leading-6 text-slate-300">
          {sanitizeDisplayText(result.test_output) || "No submitted test output was stored."}
        </pre>
      </SectionPanel>
    </div>
  );
}

function ChatMessage({ message }: { message: AITranscriptMessage }) {
  const currentFile = typeof message.metadata.current_file_path === "string" ? message.metadata.current_file_path : null;
  const confidence = typeof message.metadata.confidence === "string" ? message.metadata.confidence : null;
  const isUser = message.role === "user";
  return (
    <article
      className={cn(
        "rounded-lg border p-4 shadow-sm",
        isUser ? "border-blue-200 bg-blue-50/70" : "border-slate-200 bg-white",
      )}
    >
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={cn(
              "rounded-full border px-3 py-1 text-xs font-medium",
              isUser ? "border-blue-200 bg-white text-blue-700" : "border-slate-200 bg-slate-50 text-slate-700",
            )}
          >
            {isUser ? "Candidate" : "AI Copilot"}
          </span>
          <span className="text-xs text-slate-500">{formatDateTime(message.created_at)}</span>
        </div>
        <span className="text-xs text-slate-500">
          {confidence ? `Confidence: ${confidence}` : message.ai_mode.replace(/_/g, " ")}
        </span>
      </div>
      {currentFile ? <p className="mt-3 text-xs font-medium text-blue-700">File context: {sanitizeDisplayText(currentFile)}</p> : null}
      <div className="mt-3">
        <MarkdownBlock content={message.content} emptyLabel="No message content recorded." />
      </div>
    </article>
  );
}

function TranscriptViewer({ result }: { result: SessionResult }) {
  return (
    <div className="grid gap-5">
      <AIUsageSummary result={result} />
      <SectionPanel
        aside={<span className="text-xs uppercase tracking-wide text-slate-500">{result.ai_chat_transcript.length} messages</span>}
        description="Candidate prompts and assistant responses from the interview workspace."
        title="AI Transcript"
      >
        <div className="grid gap-3">
          {result.ai_chat_transcript.length ? (
            result.ai_chat_transcript.map((message) => <ChatMessage key={message.id} message={message} />)
          ) : (
            <EmptyState
              description="The candidate did not use the AI copilot during this interview."
              embedded
              title="No AI messages"
            />
          )}
        </div>
      </SectionPanel>
    </div>
  );
}

function eventLabel(eventType: string): string {
  return eventType
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function eventGroup(eventType: string): { key: string; label: string } {
  if (["code_edit", "file_edited", "file_saved", "file_opened"].includes(eventType)) {
    return { key: "code_activity", label: "Code edited" };
  }
  if (["ai_prompt_sent", "ai_response_received"].includes(eventType)) {
    return { key: "ai_activity", label: "AI prompts sent" };
  }
  if (["test_run_started", "test_run", "test_run_completed", "test_run_failed", "final_tests_passed", "final_tests_failed"].includes(eventType)) {
    return { key: "test_activity", label: "Tests run" };
  }
  if (eventType === "note_updated") {
    return { key: "note_activity", label: "Final explanation updated" };
  }
  if (eventType === "session_started") {
    return { key: "session_started", label: "Session started" };
  }
  if (eventType === "task_viewed") {
    return { key: "task_viewed", label: "Task viewed" };
  }
  if (["submission_created", "final_submit"].includes(eventType)) {
    return { key: "submission_created", label: "Solution submitted" };
  }
  return { key: eventType, label: eventLabel(eventType) };
}

function telemetryDetails(event: TelemetryTimelineEvent): string[] {
  const payload = event.payload;
  const lines: string[] = [];
  const path = typeof payload.path === "string" ? payload.path : null;
  const currentFile = typeof payload.current_file_path === "string" ? payload.current_file_path : null;
  const autosavedAt = typeof payload.autosaved_at === "string" ? payload.autosaved_at : null;
  const status = typeof payload.status === "string" ? payload.status : null;
  const testStatus = typeof payload.test_status === "string" ? payload.test_status : null;
  const codeLength = typeof payload.code_length === "number" ? payload.code_length : null;
  const noteLength = typeof payload.note_length === "number" ? payload.note_length : null;
  const changedFileCount = typeof payload.changed_file_count === "number" ? payload.changed_file_count : null;
  const submittedFileCount = typeof payload.submitted_file_count === "number" ? payload.submitted_file_count : null;
  const questionLength = typeof payload.question_length === "number" ? payload.question_length : null;
  const responseConfidence = typeof payload.response_confidence === "string" ? payload.response_confidence : null;

  if (path) {
    lines.push(`File: ${path}`);
  }
  if (currentFile) {
    lines.push(`Context file: ${currentFile}`);
  }
  if (status) {
    lines.push(`Status: ${status}`);
  }
  if (testStatus) {
    lines.push(`Test status: ${testStatus}`);
  }
  if (codeLength !== null) {
    lines.push(`Code size: ${codeLength} characters`);
  }
  if (noteLength !== null) {
    lines.push(`Notes size: ${noteLength} characters`);
  }
  if (changedFileCount !== null) {
    lines.push(`Changed files: ${changedFileCount}`);
  }
  if (submittedFileCount !== null) {
    lines.push(`Submitted files: ${submittedFileCount}`);
  }
  if (questionLength !== null) {
    lines.push(`Prompt length: ${questionLength} characters`);
  }
  if (responseConfidence) {
    lines.push(`Response confidence: ${responseConfidence}`);
  }
  if (autosavedAt) {
    lines.push(`Autosaved: ${formatDateTime(autosavedAt)}`);
  }

  if (!lines.length) {
    lines.push("Event recorded.");
  }
  return lines.map(sanitizeDisplayText);
}

function timelineGroups(events: TelemetryTimelineEvent[]): TimelineGroup[] {
  const groups = new Map<string, TimelineGroup>();
  for (const event of events) {
    const category = eventGroup(event.event_type);
    const existing = groups.get(category.key);
    if (existing) {
      existing.count += 1;
      existing.lastAt = event.created_at;
      existing.details = Array.from(new Set([...existing.details, ...telemetryDetails(event)])).slice(0, 5);
      continue;
    }
    groups.set(category.key, {
      id: category.key,
      eventType: event.event_type,
      label: category.label,
      count: 1,
      firstAt: event.created_at,
      lastAt: event.created_at,
      details: telemetryDetails(event),
    });
  }
  return Array.from(groups.values()).sort(
    (left, right) => new Date(left.firstAt).getTime() - new Date(right.firstAt).getTime(),
  );
}

function Timeline({ result }: { result: SessionResult }) {
  const groups = useMemo(() => timelineGroups(result.telemetry_timeline), [result.telemetry_timeline]);
  const activityCounts = useMemo(
    () => ({
      edits: result.telemetry_timeline.filter((event) => eventGroup(event.event_type).key === "code_activity").length,
      prompts: result.telemetry_timeline.filter((event) => event.event_type === "ai_prompt_sent").length,
      tests: result.telemetry_timeline.filter((event) => eventGroup(event.event_type).key === "test_activity").length,
      notes: result.telemetry_timeline.filter((event) => event.event_type === "note_updated").length,
    }),
    [result.telemetry_timeline],
  );
  return (
    <SectionPanel
      aside={<span className="text-xs uppercase tracking-wide text-slate-500">{result.telemetry_timeline.length} events</span>}
      description="Repeated activity is summarized into meaningful milestones instead of exposing a noisy event dump."
      title="Session Timeline"
    >
      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <MiniMetric label="Code Edits" value={activityCounts.edits} />
        <MiniMetric label="AI Prompts" value={activityCounts.prompts} />
        <MiniMetric label="Test Runs" value={activityCounts.tests} />
        <MiniMetric label="Explanation Updates" value={activityCounts.notes} />
      </div>
      <div className="grid gap-4">
        {groups.length ? (
          groups.map((group) => (
            <article className="relative grid gap-2 border-l-2 border-slate-200 pb-2 pl-5" key={`${group.id}-${group.firstAt}`}>
              <span className="absolute -left-[7px] top-1 h-3 w-3 rounded-full border-2 border-white bg-blue-500 shadow-sm" />
              <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                <h3 className="text-sm font-semibold text-slate-900">
                  {group.count > 1 ? `${group.label} ${group.count} times` : group.label}
                </h3>
                <span className="text-xs text-slate-500">
                  {group.count > 1 ? `${formatDateTime(group.firstAt)} to ${formatDateTime(group.lastAt)}` : formatDateTime(group.firstAt)}
                </span>
              </div>
              <ul className="grid gap-1 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs leading-5 text-slate-600">
                {group.details.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            </article>
          ))
        ) : (
          <EmptyState description="No candidate telemetry has been recorded for this session." title="No telemetry yet" />
        )}
      </div>
    </SectionPanel>
  );
}

function ReportHeader({ result, stack }: { result: SessionResult; stack: string[] }) {
  const initials = result.candidate_name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");

  return (
    <section className="relative overflow-hidden rounded-card border border-slate-200/80 bg-white/95 shadow-elevated">
      <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-blue-600 via-sky-400 to-emerald-400" />
      <div className="grid gap-6 p-5 lg:grid-cols-[minmax(0,1fr)_220px] lg:p-6">
        <div className="min-w-0">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg border border-blue-200 bg-blue-50 text-sm font-bold text-blue-700 shadow-sm">
              {initials || "C"}
            </div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge label={result.status} tone={statusTone(result.status)} />
                <RecommendationBadge recommendation={result.recommendation} />
              </div>
              <h2 className="mt-3 text-2xl font-semibold tracking-tight text-slate-950">{result.candidate_name}</h2>
              <p className="mt-1 text-sm text-slate-600">{result.candidate_email}</p>
              <h3 className="mt-4 text-lg font-semibold text-slate-900">{result.scenario_title}</h3>
              <p className="mt-1 text-sm text-slate-600">{result.role_title}</p>
              {stack.length ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  {stack.map((item) => (
                    <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-700" key={item}>
                      {item}
                    </span>
                  ))}
                </div>
              ) : null}
            </div>
          </div>
          <div className="mt-6 grid gap-3 border-t border-slate-200 pt-5 sm:grid-cols-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Submitted</p>
              <p className="mt-1 text-sm font-medium text-slate-800">{formatDateTime(result.submitted_at)}</p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Review status</p>
              <p className="mt-1 text-sm font-medium text-slate-800">
                {result.status.replace(/_/g, " ")}
              </p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Evidence set</p>
              <p className="mt-1 text-sm font-medium text-slate-800">
                {result.agent_reviews.length} agents / {result.test_runs.length} test runs
              </p>
            </div>
          </div>
        </div>
        <div className="flex min-h-44 flex-col justify-between rounded-lg border border-slate-200 bg-slate-50/90 p-5 shadow-inner">
          <div>
            <div className="flex items-center gap-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Overall score</p>
              <InfoTooltip
                content="Weighted from the completed score dimensions shown in the Overview tab."
                label="Overall score help"
              />
            </div>
            <p className="mt-3 text-5xl font-semibold tracking-tight text-slate-950">
              {result.weighted_score ?? "--"}
              <span className="ml-1 text-lg font-medium text-slate-400">/100</span>
            </p>
          </div>
          <div className="mt-5">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Final recommendation</p>
            <div className="mt-2">
              <RecommendationBadge recommendation={result.recommendation} />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function ResultTabs({
  activeTab,
  onTabChange,
}: {
  activeTab: ResultTab;
  onTabChange: (tab: ResultTab) => void;
}) {
  return (
    <div className="overflow-x-auto rounded-card border border-slate-200/80 bg-white/95 p-1.5 shadow-panel">
      <div className="flex min-w-max gap-1">
        {RESULT_TABS.map((tab) => (
          <button
            className={cn(
              "h-10 rounded-lg px-4 text-sm font-semibold outline-none transition",
              activeTab === tab.id
                ? "bg-slate-950 text-white shadow-sm"
                : "text-slate-600 hover:bg-slate-100 hover:text-slate-950",
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

function ResultTabContent({ activeTab, result }: { activeTab: ResultTab; result: SessionResult }) {
  if (activeTab === "agents") {
    return <AgentReviews result={result} />;
  }
  if (activeTab === "code") {
    return <CodeSubmission result={result} />;
  }
  if (activeTab === "tests") {
    return <TestReport result={result} />;
  }
  if (activeTab === "transcript") {
    return <TranscriptViewer result={result} />;
  }
  if (activeTab === "timeline") {
    return <Timeline result={result} />;
  }
  return <ResultOverview result={result} />;
}

function ResultContent() {
  const params = useParams<{ sessionId: string }>();
  const { token, user } = useAuth();
  const [result, setResult] = useState<SessionResult | null>(null);
  const [interviewStack, setInterviewStack] = useState<string[]>([]);
  const [activeTab, setActiveTab] = useState<ResultTab>("overview");
  const [isLoading, setIsLoading] = useState(true);
  const [isReviewing, setIsReviewing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canReview = user?.role === "ADMIN" || user?.role === "INTERVIEWER";

  const loadResult = useCallback(async () => {
    if (!token || !params.sessionId || !canReview) {
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const loadedResult = await getSessionResult(token, params.sessionId);
      setResult(loadedResult);
      try {
        const interview = await getInterview(token, loadedResult.interview_id);
        setInterviewStack(interview.stack);
      } catch {
        setInterviewStack([]);
      }
    } catch (requestError: unknown) {
      if (requestError instanceof ApiError && requestError.status === 404) {
        setError("Result is not ready yet. Ask the candidate to submit or run the review once a submission exists.");
      } else {
        setError("Failed to load this result. Try again in a moment.");
      }
    } finally {
      setIsLoading(false);
    }
  }, [canReview, params.sessionId, token]);

  useEffect(() => {
    void loadResult();
  }, [loadResult]);

  async function handleRunReview() {
    if (!token || !result) {
      return;
    }
    setIsReviewing(true);
    setError(null);
    try {
      const reviewed = await runSubmissionReview(token, result.submission_id);
      setResult({ ...result, ...reviewed });
      setActiveTab("agents");
    } catch {
      setError("Review agents could not run right now. Try again in a moment.");
    } finally {
      setIsReviewing(false);
    }
  }

  if (!canReview) {
    return (
      <AppShell>
        <PageHeader
          description="Submission results are available to admin and interviewer roles."
          eyebrow="Access"
          title="Submission result"
        />
        <div className="mt-6">
          <EmptyState description="Your current role cannot review interview submissions." title="Result unavailable" />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <PageHeader
        actions={
          result ? (
            result.agent_reviews.length > 0 ? (
              <StatusBadge label="Review complete" tone="success" />
            ) : (
              <Button
                aria-busy={isReviewing}
                disabled={isReviewing}
                onClick={() => void handleRunReview()}
                type="button"
              >
                {isReviewing ? "Reviewing..." : "Run agent review"}
              </Button>
            )
          ) : null
        }
        description="A structured, evidence-backed assessment of engineering judgment, execution, validation, and AI collaboration."
        eyebrow="Engineering evaluation"
        title="Candidate evaluation report"
      />

      <main className="mt-6 grid max-w-7xl gap-5">
        <Link className="w-fit text-sm font-semibold text-blue-700 hover:text-blue-900" href="/results">
          Back to results
        </Link>

        {isLoading ? <LoadingState label="Loading result" rows={4} /> : null}
        {error ? (
          <div className="grid gap-3">
            <ErrorState message={error} />
            <Button className="w-fit" onClick={() => void loadResult()} type="button" variant="secondary">
              Retry
            </Button>
          </div>
        ) : null}

        {!isLoading && !error && !result ? (
          <EmptyState
            description="The candidate submission exists, but review data is not available yet."
            title="Results not ready"
          />
        ) : null}

        {result ? (
          <section className="grid gap-5">
            <ReportHeader result={result} stack={interviewStack} />
            <ResultTabs activeTab={activeTab} onTabChange={setActiveTab} />
            <ResultTabContent activeTab={activeTab} result={result} />
          </section>
        ) : null}
      </main>
    </AppShell>
  );
}

export default function ResultPage() {
  return (
    <ProtectedRoute>
      <ResultContent />
    </ProtectedRoute>
  );
}
