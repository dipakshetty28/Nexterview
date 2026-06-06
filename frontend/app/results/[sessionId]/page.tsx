"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { type ReactNode, useCallback, useEffect, useMemo, useState } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { AppShell } from "@/components/app/app-shell";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  StatusBadge,
  formatDateTime,
  statusTone,
} from "@/components/app/page-primitives";
import { useAuth } from "@/components/auth/auth-provider";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { Button } from "@/components/ui/button";
import { ApiError, getSessionResult, runSubmissionReview } from "@/lib/api";
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

type ResultTab = "overview" | "agents" | "code" | "transcript" | "timeline" | "notes";

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
  { id: "code", label: "Code Submission" },
  { id: "transcript", label: "AI Transcript" },
  { id: "timeline", label: "Timeline" },
  { id: "notes", label: "Notes" },
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
    <section className="rounded-card border border-white/80 bg-white p-5 shadow-panel">
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
    <div className="rounded-lg border border-slate-200 bg-slate-50/90 p-3">
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
      <ul className="mt-2 grid gap-1 text-sm leading-6 text-slate-700">
        {items.length ? (
          items.map((item) => <li key={item}>{sanitizeDisplayText(item)}</li>)
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
        <span className="rounded-full border border-amber-900/70 bg-amber-950/30 px-3 py-1 text-xs text-amber-100" key={flag}>
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
  const chartData = result.score_breakdown.map((item) => ({
    name: scoreLabel(item),
    score: item.score ?? 0,
    weight: item.weight,
  }));
  return (
    <SectionPanel
      description="Weighted dimensions used by reviewer agents."
      title="Score Breakdown"
    >
      {result.score_breakdown.length ? (
        <div className="grid gap-5 xl:grid-cols-[minmax(0,1.3fr)_minmax(320px,0.7fr)]">
          <div className="h-80 min-w-0">
            <ResponsiveContainer height="100%" width="100%">
              <BarChart data={chartData} margin={{ bottom: 24, left: -16, right: 8, top: 8 }}>
                <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
                <XAxis angle={-18} dataKey="name" height={62} interval={0} stroke="#64748b" textAnchor="end" tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 100]} stroke="#64748b" />
                <Tooltip contentStyle={{ background: "#ffffff", border: "1px solid #cbd5e1", color: "#0f172a", borderRadius: "12px" }} />
                <Bar dataKey="score" fill="#2563eb" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="grid content-start gap-2">
            {result.score_breakdown.map((item) => (
              <div className="grid grid-cols-[1fr_auto] items-center gap-3 rounded-lg border border-slate-200 bg-slate-50/90 p-3" key={item.agent_type}>
                <div>
                  <p className="text-sm font-medium text-slate-900">{scoreLabel(item)}</p>
                  <p className="text-xs text-slate-500">Weight {item.weight}%</p>
                </div>
                <span className={cn("rounded-full border px-2.5 py-1 text-sm font-semibold", scoreTone(item.score))}>
                  {item.score ?? "--"}
                </span>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <EmptyState description="Run the agent review to populate score dimensions." title="Score breakdown not ready" />
      )}
    </SectionPanel>
  );
}

function ResultOverview({ result }: { result: SessionResult }) {
  return (
    <div className="grid gap-5">
      <div className="grid gap-5 xl:grid-cols-[360px_minmax(0,1fr)]">
        <section className="rounded-card border border-white/80 bg-white p-5 shadow-panel">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Final Recommendation</p>
          <div className="mt-3">
            <RecommendationBadge recommendation={result.recommendation} />
          </div>
          <p className="mt-4 text-5xl font-semibold text-slate-950">{result.weighted_score ?? "--"}</p>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Overall weighted score from agent reviews. Pending submissions stay unscored until review is complete.
          </p>
        </section>

        <section className="rounded-card border border-white/80 bg-white p-5 shadow-panel">
          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div>
              <p className="text-sm font-medium text-blue-700">{result.role_title}</p>
              <h2 className="mt-1 text-xl font-semibold text-slate-950">{result.scenario_title}</h2>
              <p className="mt-2 text-sm text-slate-600">
                {result.candidate_name} / {result.candidate_email}
              </p>
            </div>
            <StatusBadge label={result.status} tone={statusTone(result.status)} />
          </div>
          <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <MiniMetric label="Submitted" value={formatDateTime(result.submitted_at)} />
            <MiniMetric label="Changed Files" value={result.changed_files.length} />
            <MiniMetric label="AI Prompts" value={result.ai_usage_analysis.candidate_prompt_count} />
            <MiniMetric label="Test Runs" value={result.ai_usage_analysis.test_run_count} />
          </div>
        </section>
      </div>

      <SectionPanel
        description="Stored validation attempts from the candidate workspace and final submission."
        title="Test Validation"
      >
        {result.test_runs.length ? (
          <div className="grid gap-3 md:grid-cols-3">
            <MiniMetric label="Attempts" value={result.test_runs.length} />
            <MiniMetric label="First Run" value={result.test_runs[0]?.status ?? "n/a"} />
            <MiniMetric label="Final Run" value={result.test_runs[result.test_runs.length - 1]?.status ?? "n/a"} />
            <div className="overflow-x-auto rounded-lg border border-slate-200 bg-slate-50/70 md:col-span-3">
              <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
                <thead className="text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-3 py-2 font-medium">When</th>
                    <th className="px-3 py-2 font-medium">Status</th>
                    <th className="px-3 py-2 font-medium">Command</th>
                    <th className="px-3 py-2 font-medium">Pass/Fail</th>
                    <th className="px-3 py-2 font-medium">Summary</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {result.test_runs.map((run) => (
                    <tr key={run.id}>
                      <td className="px-3 py-2 text-slate-600">{formatDateTime(run.created_at)}</td>
                      <td className="px-3 py-2">
                        <StatusBadge label={run.status} tone={run.status === "passed" ? "success" : "warning"} />
                      </td>
                      <td className="px-3 py-2 font-mono text-xs text-blue-700">{sanitizeDisplayText(run.command)}</td>
                      <td className="px-3 py-2 text-slate-700">
                        {run.passed_count}/{run.total_count} passed
                      </td>
                      <td className="max-w-sm px-3 py-2 text-slate-600">{sanitizeDisplayText(run.failure_summary) || "All checks passed."}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <EmptyState description="No validation attempts have been recorded for this session." title="No test runs yet" />
        )}
      </SectionPanel>

      <ScoreBreakdown result={result} />

      <div className="grid gap-5 lg:grid-cols-2">
        <SectionPanel title="AI Usage Summary">
          <MarkdownBlock content={result.ai_usage_analysis.summary} emptyLabel="No AI usage summary is available." />
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <MiniMetric label="Responses" value={result.ai_usage_analysis.assistant_response_count} />
            <MiniMetric label="Prompts With File Context" value={result.ai_usage_analysis.prompts_with_file_context} />
            <MiniMetric
              label="Validated Suggestions"
              value={result.ai_usage_analysis.validated_suggestions ? "Yes" : "Not evident"}
            />
            <MiniMetric
              label="Confidence Signals"
              value={result.ai_usage_analysis.response_confidence_values.length || "None"}
            />
          </div>
        </SectionPanel>

        <SectionPanel title="Prompt Quality">
          <MarkdownBlock content={result.prompt_quality_summary.summary} emptyLabel="No prompt quality analysis is available." />
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <MiniMetric label="Vague Prompts" value={result.prompt_quality_summary.vague_prompt_count} />
            <MiniMetric label="Validation Prompts" value={result.prompt_quality_summary.validation_prompt_count} />
            <MiniMetric label="Average Length" value={Math.round(result.prompt_quality_summary.average_prompt_length)} />
            <MiniMetric label="File Context" value={result.prompt_quality_summary.prompts_with_file_context} />
          </div>
        </SectionPanel>
      </div>

      <SectionPanel title="Risk Flags">
        <RiskFlagList flags={result.risk_flags} />
      </SectionPanel>
    </div>
  );
}

function AgentReviewCard({ review }: { review: AgentReview }) {
  return (
    <section className="grid gap-4 rounded-card border border-white/80 bg-white p-5 shadow-panel">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{review.agent_type.replace(/_/g, " ")}</p>
          <h3 className="mt-1 text-base font-semibold text-slate-950">{review.agent_label}</h3>
          <div className="mt-3">
            <RecommendationBadge recommendation={review.recommendation} />
          </div>
        </div>
        <span className={cn("w-fit rounded-full border px-3 py-1 text-sm font-semibold", scoreTone(review.score))}>
          Score {review.score}
        </span>
      </div>
      {review.review_source ? (
        <p className="text-xs uppercase tracking-wide text-slate-500">
          Source: {review.review_source.replace(/_/g, " ")}
          {review.confidence !== null && review.confidence !== undefined ? ` / confidence ${Math.round(review.confidence * 100)}%` : ""}
        </p>
      ) : null}
      <MarkdownBlock content={review.explanation} emptyLabel="No reviewer explanation was recorded." />
      <div className="grid gap-4 md:grid-cols-2">
        <TextList items={review.expected} title="Expected" />
        <TextList items={review.observed} title="Observed" />
        <TextList items={review.strengths} title="Strengths" />
        <TextList items={review.weaknesses} title="Weaknesses" />
        <TextList items={review.evidence} title="Evidence" />
        <TextList items={review.risk_flags} title="Risk Flags" />
        <TextList items={review.follow_up_questions} title="Follow-Up Questions" />
      </div>
    </section>
  );
}

function AgentReviews({ result }: { result: SessionResult }) {
  return (
    <div className="grid gap-4">
      {result.agent_reviews.length ? (
        result.agent_reviews.map((review) => <AgentReviewCard key={review.id} review={review} />)
      ) : (
        <EmptyState description="The submission is saved, but agent review output is not ready yet." title="Review still running" />
      )}
    </div>
  );
}

function CodeSubmission({ result }: { result: SessionResult }) {
  return (
    <div className="grid gap-5">
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

function ChatMessage({ message }: { message: AITranscriptMessage }) {
  const currentFile = typeof message.metadata.current_file_path === "string" ? message.metadata.current_file_path : null;
  const confidence = typeof message.metadata.confidence === "string" ? message.metadata.confidence : null;
  const isUser = message.role === "user";
  return (
    <article
      className={cn(
        "rounded-md border p-4",
        isUser ? "border-cyan-900/70 bg-cyan-950/20" : "border-slate-800 bg-slate-950",
      )}
    >
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={cn(
              "rounded-full border px-3 py-1 text-xs font-medium",
              isUser ? "border-cyan-800 text-cyan-100" : "border-slate-700 text-slate-300",
            )}
          >
            {isUser ? "Candidate" : "AI Copilot"}
          </span>
          <span className="text-xs text-slate-500">{formatDateTime(message.created_at)}</span>
        </div>
        <span className="text-xs text-slate-500">{confidence ? `Confidence: ${confidence}` : message.ai_mode}</span>
      </div>
      {currentFile ? <p className="mt-3 text-xs text-cyan-300">File context: {sanitizeDisplayText(currentFile)}</p> : null}
      <div className="mt-3">
        <MarkdownBlock content={message.content} emptyLabel="No message content recorded." />
      </div>
    </article>
  );
}

function TranscriptViewer({ result }: { result: SessionResult }) {
  return (
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
            title="No AI messages"
          />
        )}
      </div>
    </SectionPanel>
  );
}

function groupableEventType(eventType: string): boolean {
  return ["code_edit", "file_edited", "file_saved", "note_updated"].includes(eventType);
}

function eventLabel(eventType: string): string {
  return eventType
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
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
  const groups: TimelineGroup[] = [];
  for (const event of events) {
    const path =
      typeof event.payload.path === "string"
        ? event.payload.path
        : typeof event.payload.current_file_path === "string"
          ? event.payload.current_file_path
          : "";
    const groupingKey = groupableEventType(event.event_type) ? `${event.event_type}:${path}` : event.id;
    const previous = groups[groups.length - 1];
    if (previous && previous.id === groupingKey && groupableEventType(event.event_type)) {
      previous.count += 1;
      previous.lastAt = event.created_at;
      previous.details = Array.from(new Set([...previous.details, ...telemetryDetails(event)])).slice(0, 5);
      continue;
    }
    groups.push({
      id: groupingKey,
      eventType: event.event_type,
      label: eventLabel(event.event_type),
      count: 1,
      firstAt: event.created_at,
      lastAt: event.created_at,
      details: telemetryDetails(event),
    });
  }
  return groups;
}

function Timeline({ result }: { result: SessionResult }) {
  const groups = useMemo(() => timelineGroups(result.telemetry_timeline), [result.telemetry_timeline]);
  return (
    <SectionPanel
      aside={<span className="text-xs uppercase tracking-wide text-slate-500">{result.telemetry_timeline.length} events</span>}
      description="Repeated edit and note events are grouped so reviewers can see meaningful activity without raw event noise."
      title="Telemetry Timeline"
    >
      <div className="grid gap-4">
        {groups.length ? (
          groups.map((group) => (
            <article className="grid gap-2 border-l border-slate-700 pl-4" key={`${group.id}-${group.firstAt}`}>
              <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                <h3 className="text-sm font-medium text-slate-100">
                  {group.label}
                  {group.count > 1 ? <span className="ml-2 text-xs text-slate-500">x{group.count}</span> : null}
                </h3>
                <span className="text-xs text-slate-500">
                  {group.count > 1 ? `${formatDateTime(group.firstAt)} to ${formatDateTime(group.lastAt)}` : formatDateTime(group.firstAt)}
                </span>
              </div>
              <ul className="grid gap-1 rounded-md bg-slate-950 p-3 text-xs leading-5 text-slate-400">
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

function NotesTab({ result }: { result: SessionResult }) {
  return (
    <div className="grid gap-5">
      <SectionPanel title="Candidate Explanation">
        <MarkdownBlock content={result.notes} emptyLabel="No candidate explanation was submitted." />
      </SectionPanel>
      <SectionPanel title="Submitted Test Output">
        <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-md border border-slate-800 bg-slate-950 p-3 text-sm leading-6 text-slate-300">
          {sanitizeDisplayText(result.test_output) || "No submitted test output."}
        </pre>
      </SectionPanel>
      <SectionPanel title="Scenario Signals">
        <div className="grid gap-4 lg:grid-cols-2">
          <div>
            <h3 className="text-sm font-semibold text-slate-100">Bug Report</h3>
            <MarkdownBlock content={result.bug_description} emptyLabel="No bug report was stored." />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-100">Feature Request</h3>
            <MarkdownBlock content={result.feature_request} emptyLabel="No feature request was stored." />
          </div>
          <div className="lg:col-span-2">
            <h3 className="text-sm font-semibold text-slate-100">Visible Validation Guidance</h3>
            <MarkdownBlock content={result.validation_instructions} emptyLabel="No validation guidance was stored." />
          </div>
        </div>
      </SectionPanel>
      <SectionPanel
        description="Interviewer-only review context used to compare the candidate submission against the intended solution."
        title="Expected Outcome"
      >
        <div className="grid gap-4 lg:grid-cols-2">
          <TextList items={result.expected_behavior} title="Expected Behavior" />
          <TextList items={result.hidden_evaluation_points} title="Hidden Evaluation Points" />
          <TextList items={result.interviewer_rubric} title="Interviewer Rubric" />
          <TextList items={result.candidate_observed} title="What Candidate Did" />
          <TextList items={result.candidate_missed} title="What Candidate Missed" />
          <TextList items={result.suggested_follow_up_questions} title="Suggested Follow-Up" />
          <div className="lg:col-span-2">
            <h3 className="text-sm font-semibold text-slate-100">Expected Solution Summary</h3>
            <MarkdownBlock content={result.expected_solution_summary} emptyLabel="No expected solution summary was stored." />
          </div>
        </div>
      </SectionPanel>
      <SectionPanel title="Prompt Quality Details">
        <div className="grid gap-4 md:grid-cols-2">
          <TextList items={result.prompt_quality_summary.strengths} title="Prompt Strengths" />
          <TextList items={result.prompt_quality_summary.risks} title="Prompt Risks" />
        </div>
      </SectionPanel>
    </div>
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
    <div className="overflow-x-auto rounded-card border border-white/80 bg-white p-1 shadow-panel">
      <div className="flex min-w-max gap-1">
        {RESULT_TABS.map((tab) => (
          <button
            className={cn(
              "h-10 rounded-lg px-4 text-sm font-semibold outline-none transition",
              activeTab === tab.id
                ? "bg-blue-600 text-white shadow-sm"
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
  if (activeTab === "transcript") {
    return <TranscriptViewer result={result} />;
  }
  if (activeTab === "timeline") {
    return <Timeline result={result} />;
  }
  if (activeTab === "notes") {
    return <NotesTab result={result} />;
  }
  return <ResultOverview result={result} />;
}

function ResultContent() {
  const params = useParams<{ sessionId: string }>();
  const { token, user } = useAuth();
  const [result, setResult] = useState<SessionResult | null>(null);
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
            <Button
              aria-busy={isReviewing}
              disabled={isReviewing || result.agent_reviews.length > 0}
              onClick={() => void handleRunReview()}
              type="button"
            >
              {isReviewing ? "Reviewing..." : result.agent_reviews.length > 0 ? "Review complete" : "Run agent review"}
            </Button>
          ) : null
        }
        description="Review candidate code, agent analysis, score breakdown, AI usage, and summarized telemetry."
        eyebrow="Submission review"
        title="Submission result"
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
            <section className="rounded-card border border-white/80 bg-white p-5 shadow-panel">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge label={result.status} tone={statusTone(result.status)} />
                    <RecommendationBadge recommendation={result.recommendation} />
                  </div>
                  <h2 className="mt-4 text-2xl font-semibold text-slate-950">{result.scenario_title}</h2>
                  <p className="mt-2 text-sm leading-6 text-slate-600">
                    {result.role_title} / {result.candidate_name} / {result.candidate_email}
                  </p>
                </div>
                <div className={cn("w-fit rounded-md border px-4 py-3", scoreTone(result.weighted_score))}>
                  <p className="text-xs uppercase tracking-wide opacity-80">Overall Score</p>
                  <p className="mt-1 text-2xl font-semibold">{result.weighted_score ?? "--"}</p>
                </div>
              </div>
            </section>

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
