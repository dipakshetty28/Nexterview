"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { useAuth } from "@/components/auth/auth-provider";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { Button } from "@/components/ui/button";
import { ApiError, getSessionResult, runSubmissionReview } from "@/lib/api";
import type { AgentReview, AITranscriptMessage, FileDiff, GitHubReviewLinks, SessionResult, TelemetryTimelineEvent } from "@/lib/types";

function branchUrl(github: GitHubReviewLinks): string | null {
  if (!github.repository_url || !github.branch_name) {
    return null;
  }
  return `${github.repository_url}/tree/${encodeURIComponent(github.branch_name)}`;
}

function scoreTone(score: number | null): string {
  if (score === null) {
    return "border-slate-700 bg-slate-950 text-slate-300";
  }
  if (score >= 80) {
    return "border-emerald-900/70 bg-emerald-950/30 text-emerald-200";
  }
  if (score >= 65) {
    return "border-cyan-900/70 bg-cyan-950/30 text-cyan-200";
  }
  if (score >= 50) {
    return "border-amber-900/70 bg-amber-950/30 text-amber-200";
  }
  return "border-red-900/70 bg-red-950/30 text-red-200";
}

function GitHubLinks({ github }: { github: GitHubReviewLinks }) {
  const branchHref = branchUrl(github);
  if (github.push_status === "pushed") {
    return (
      <div className="flex flex-wrap gap-3 text-sm">
        {branchHref ? (
          <a className="font-medium text-cyan-300 hover:text-cyan-200" href={branchHref}>
            Branch: {github.branch_name}
          </a>
        ) : (
          <span className="text-slate-300">Branch: {github.branch_name}</span>
        )}
        {github.pull_request_url ? (
          <a className="font-medium text-cyan-300 hover:text-cyan-200" href={github.pull_request_url}>
            Pull request
          </a>
        ) : null}
        {github.base_branch_name ? <span className="text-slate-500">Base: {github.base_branch_name}</span> : null}
      </div>
    );
  }
  if (github.push_status === "failed") {
    return <p className="text-sm text-amber-300">GitHub push failed; database submission was preserved.</p>;
  }
  if (github.push_status === "no_changes") {
    return <p className="text-sm text-slate-400">No changed files were pushed to GitHub.</p>;
  }
  return <p className="text-sm text-slate-400">GitHub push disabled; reviewing database submission.</p>;
}

function ReviewList({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</h4>
      <ul className="mt-2 grid gap-1 text-sm leading-6 text-slate-300">
        {items.length ? items.map((item) => <li key={item}>{item}</li>) : <li className="text-slate-500">None recorded.</li>}
      </ul>
    </div>
  );
}

function DiffBlock({ diff }: { diff: FileDiff }) {
  return (
    <details className="rounded-md border border-slate-800 bg-slate-950">
      <summary className="cursor-pointer px-3 py-2 text-sm">
        <span className="font-medium text-slate-100">{diff.path}</span>
        <span className="ml-2 text-xs text-slate-500">
          {diff.status} / +{diff.additions} -{diff.deletions}
        </span>
      </summary>
      <pre className="max-h-96 overflow-auto border-t border-slate-800 p-3 text-xs leading-5 text-slate-200">
        {diff.diff || "No textual diff available."}
      </pre>
    </details>
  );
}

function AgentReviewCard({ review }: { review: AgentReview }) {
  return (
    <section className="grid gap-4 rounded-md border border-slate-800 bg-slate-900/70 p-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-base font-semibold text-slate-100">{review.agent_label}</h3>
          <p className="mt-1 text-sm text-slate-400">{review.recommendation}</p>
        </div>
        <span className={`w-fit rounded-md border px-3 py-1 text-sm font-semibold ${scoreTone(review.score)}`}>
          {review.score}
        </span>
      </div>
      <p className="text-sm leading-6 text-slate-300">{review.explanation}</p>
      <div className="grid gap-4 md:grid-cols-2">
        <ReviewList items={review.strengths} title="Strengths" />
        <ReviewList items={review.weaknesses} title="Weaknesses" />
        <ReviewList items={review.evidence} title="Evidence" />
        <ReviewList items={review.risk_flags} title="Risk Flags" />
      </div>
    </section>
  );
}

function ScoreBreakdownChart({ result }: { result: SessionResult }) {
  const data = result.score_breakdown.map((item) => ({
    name: item.label.replace(" Agent", ""),
    score: item.score ?? 0,
    weight: item.weight,
  }));
  return (
    <div className="h-72">
      <ResponsiveContainer height="100%" width="100%">
        <BarChart data={data}>
          <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
          <XAxis dataKey="name" stroke="#94a3b8" tick={{ fontSize: 11 }} />
          <YAxis domain={[0, 100]} stroke="#94a3b8" />
          <Tooltip contentStyle={{ background: "#020617", border: "1px solid #334155", color: "#e2e8f0" }} />
          <Bar dataKey="score" fill="#06b6d4" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function SubmittedCode({ result }: { result: SessionResult }) {
  return (
    <section className="grid gap-4 rounded-md border border-slate-800 bg-slate-900/70 p-5">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <h2 className="text-lg font-semibold">Submitted code</h2>
        <span className="text-xs uppercase tracking-wide text-slate-500">{result.submitted_files.length} files</span>
      </div>
      <div className="grid gap-3">
        {result.submitted_files.length ? (
          result.submitted_files.map((file) => (
            <details className="rounded-md border border-slate-800 bg-slate-950" key={file.path}>
              <summary className="cursor-pointer px-3 py-2 text-sm">
                <span className="font-medium text-slate-100">{file.path}</span>
                <span className="ml-2 text-xs text-slate-500">
                  {file.language}
                  {file.file_type ? ` / ${file.file_type}` : ""}
                </span>
              </summary>
              <pre className="max-h-96 overflow-auto border-t border-slate-800 p-3 text-xs leading-5 text-slate-200">
                {file.content}
              </pre>
            </details>
          ))
        ) : (
          <p className="text-sm text-slate-500">No submitted files were stored.</p>
        )}
      </div>
    </section>
  );
}

function ChatMessage({ message }: { message: AITranscriptMessage }) {
  const currentFile = typeof message.metadata.current_file_path === "string" ? message.metadata.current_file_path : null;
  const confidence = typeof message.metadata.confidence === "string" ? message.metadata.confidence : null;
  return (
    <article className="rounded-md border border-slate-800 bg-slate-950 p-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full border border-slate-700 px-3 py-1 text-xs font-medium text-slate-300">{message.role}</span>
          <span className="text-xs text-slate-500">{new Date(message.created_at).toLocaleString()}</span>
        </div>
        <span className="text-xs text-slate-500">{confidence ? `Confidence: ${confidence}` : message.ai_model ?? message.ai_mode}</span>
      </div>
      {currentFile ? <p className="mt-2 text-xs text-cyan-300">File context: {currentFile}</p> : null}
      <pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap text-sm leading-6 text-slate-300">{message.content}</pre>
    </article>
  );
}

function AITranscript({ result }: { result: SessionResult }) {
  return (
    <section className="grid gap-4 rounded-md border border-slate-800 bg-slate-900/70 p-5">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <h2 className="text-lg font-semibold">AI chat transcript</h2>
        <span className="text-xs uppercase tracking-wide text-slate-500">{result.ai_chat_transcript.length} messages</span>
      </div>
      <div className="grid gap-3">
        {result.ai_chat_transcript.length ? (
          result.ai_chat_transcript.map((message) => <ChatMessage key={message.id} message={message} />)
        ) : (
          <p className="text-sm text-slate-500">Candidate did not use the AI copilot.</p>
        )}
      </div>
    </section>
  );
}

function TimelineEvent({ event }: { event: TelemetryTimelineEvent }) {
  return (
    <article className="grid gap-2 border-l border-slate-700 pl-4">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <h3 className="text-sm font-medium text-slate-100">{event.event_type}</h3>
        <span className="text-xs text-slate-500">{new Date(event.created_at).toLocaleString()}</span>
      </div>
      <pre className="max-h-40 overflow-auto whitespace-pre-wrap rounded-md bg-slate-950 p-3 text-xs leading-5 text-slate-400">
        {JSON.stringify(event.payload, null, 2)}
      </pre>
    </article>
  );
}

function TelemetryTimeline({ result }: { result: SessionResult }) {
  return (
    <section className="grid gap-4 rounded-md border border-slate-800 bg-slate-900/70 p-5">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <h2 className="text-lg font-semibold">Telemetry timeline</h2>
        <span className="text-xs uppercase tracking-wide text-slate-500">{result.telemetry_timeline.length} events</span>
      </div>
      <div className="grid gap-4">
        {result.telemetry_timeline.length ? (
          result.telemetry_timeline.map((event) => <TimelineEvent event={event} key={event.id} />)
        ) : (
          <p className="text-sm text-slate-500">No telemetry events were recorded.</p>
        )}
      </div>
    </section>
  );
}

function PromptQuality({ result }: { result: SessionResult }) {
  const summary = result.prompt_quality_summary;
  return (
    <section className="grid gap-4 rounded-md border border-slate-800 bg-slate-900/70 p-5">
      <h2 className="text-lg font-semibold">Prompt quality summary</h2>
      <p className="text-sm leading-6 text-slate-300">{summary.summary}</p>
      <div className="grid gap-3 text-sm md:grid-cols-5">
        <span className="rounded-md border border-slate-800 bg-slate-950 p-3">Prompts: {summary.candidate_prompt_count}</span>
        <span className="rounded-md border border-slate-800 bg-slate-950 p-3">File context: {summary.prompts_with_file_context}</span>
        <span className="rounded-md border border-slate-800 bg-slate-950 p-3">Vague: {summary.vague_prompt_count}</span>
        <span className="rounded-md border border-slate-800 bg-slate-950 p-3">Validation: {summary.validation_prompt_count}</span>
        <span className="rounded-md border border-slate-800 bg-slate-950 p-3">Avg chars: {summary.average_prompt_length}</span>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <ReviewList items={summary.strengths} title="Prompt Strengths" />
        <ReviewList items={summary.risks} title="Prompt Risks" />
      </div>
    </section>
  );
}

function RiskFlags({ result }: { result: SessionResult }) {
  return (
    <section className="grid gap-3 rounded-md border border-slate-800 bg-slate-900/70 p-5">
      <h2 className="text-lg font-semibold">Risk flags</h2>
      {result.risk_flags.length ? (
        <div className="flex flex-wrap gap-2">
          {result.risk_flags.map((flag) => (
            <span className="rounded-full border border-amber-900/70 bg-amber-950/30 px-3 py-1 text-xs text-amber-100" key={flag}>
              {flag}
            </span>
          ))}
        </div>
      ) : (
        <p className="text-sm text-slate-500">No cross-agent risk flags recorded.</p>
      )}
    </section>
  );
}

function ResultContent() {
  const params = useParams<{ sessionId: string }>();
  const { token, user } = useAuth();
  const [result, setResult] = useState<SessionResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isReviewing, setIsReviewing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canReview = user?.role === "ADMIN" || user?.role === "INTERVIEWER";

  useEffect(() => {
    if (!token || !params.sessionId || !canReview) {
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    getSessionResult(token, params.sessionId)
      .then((loadedResult) => setResult(loadedResult))
      .catch((requestError: unknown) => {
        const message = requestError instanceof ApiError ? requestError.message : "Unable to load result.";
        setError(message);
      })
      .finally(() => setIsLoading(false));
  }, [canReview, params.sessionId, token]);

  async function handleRunReview() {
    if (!token || !result) {
      return;
    }
    setIsReviewing(true);
    setError(null);
    try {
      const reviewed = await runSubmissionReview(token, result.submission_id);
      setResult({ ...result, ...reviewed });
    } catch (requestError: unknown) {
      const message = requestError instanceof ApiError ? requestError.message : "Unable to run review agents.";
      setError(message);
    } finally {
      setIsReviewing(false);
    }
  }

  if (!canReview) {
    return (
      <main className="min-h-screen bg-slate-950 px-6 py-8 text-slate-100">
        <div className="mx-auto max-w-3xl rounded-md border border-slate-800 bg-slate-900/70 p-6">
          <h1 className="text-2xl font-semibold">Submission result</h1>
          <p className="mt-3 text-sm text-slate-400">Your role cannot review interview submissions.</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-950/95">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-6 py-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <Link className="text-sm font-medium text-cyan-300 hover:text-cyan-200" href="/interviews">
              Back to interviews
            </Link>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight">Submission result</h1>
          </div>
          {result ? (
            <Button disabled={isReviewing || result.agent_reviews.length > 0} onClick={() => void handleRunReview()} type="button">
              {isReviewing ? "Reviewing..." : result.agent_reviews.length > 0 ? "Review complete" : "Run agent review"}
            </Button>
          ) : null}
        </div>
      </header>

      <section className="mx-auto grid max-w-6xl gap-5 px-6 py-8">
        {isLoading ? (
          <div className="rounded-md border border-slate-800 bg-slate-900/70 p-6 text-slate-300">Loading result...</div>
        ) : null}
        {error ? (
          <p className="rounded-md border border-red-900/70 bg-red-950/50 px-3 py-2 text-sm text-red-200">{error}</p>
        ) : null}
        {result ? (
          <>
            <section className="grid gap-4 rounded-md border border-slate-800 bg-slate-900/70 p-5">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <p className="text-sm text-cyan-200">{result.role_title}</p>
                  <h2 className="mt-1 text-xl font-semibold">{result.scenario_title}</h2>
                  <p className="mt-2 text-sm text-slate-400">
                    {result.candidate_name} / {result.candidate_email}
                  </p>
                </div>
                <div className={`w-fit rounded-md border px-4 py-3 ${scoreTone(result.weighted_score)}`}>
                  <p className="text-xs uppercase tracking-wide opacity-80">Weighted score</p>
                  <p className="mt-1 text-2xl font-semibold">{result.weighted_score ?? "--"}</p>
                  <p className="mt-1 text-sm">{result.recommendation ?? "Pending review"}</p>
                </div>
              </div>
              <GitHubLinks github={result.github} />
            </section>

            <section className="grid gap-4 rounded-md border border-slate-800 bg-slate-900/70 p-5">
              <h2 className="text-lg font-semibold">Score breakdown</h2>
              <ScoreBreakdownChart result={result} />
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                {result.score_breakdown.map((item) => (
                  <div className={`rounded-md border p-3 ${scoreTone(item.score)}`} key={item.agent_type}>
                    <p className="text-sm font-medium">{item.label}</p>
                    <p className="mt-2 text-xs opacity-80">Weight {item.weight}%</p>
                    <p className="mt-1 text-xl font-semibold">{item.score ?? "--"}</p>
                  </div>
                ))}
              </div>
            </section>

            <RiskFlags result={result} />

            <section className="grid gap-4 rounded-md border border-slate-800 bg-slate-900/70 p-5">
              <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                <h2 className="text-lg font-semibold">Changed files and diffs</h2>
                <span className="text-xs uppercase tracking-wide text-slate-500">{result.changed_files.length} files</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {result.changed_files.length ? (
                  result.changed_files.map((path) => (
                    <span className="rounded-full border border-cyan-900/70 bg-cyan-950/30 px-3 py-1 text-xs text-cyan-100" key={path}>
                      {path}
                    </span>
                  ))
                ) : (
                  <span className="text-sm text-slate-500">No changed files detected.</span>
                )}
              </div>
              <div className="grid gap-3">
                {result.file_diffs.map((diff) => (
                  <DiffBlock diff={diff} key={diff.path} />
                ))}
              </div>
            </section>

            <SubmittedCode result={result} />

            <section className="grid gap-4 rounded-md border border-slate-800 bg-slate-900/70 p-5">
              <h2 className="text-lg font-semibold">AI usage analysis</h2>
              <p className="text-sm leading-6 text-slate-300">{result.ai_usage_analysis.summary}</p>
              <div className="grid gap-3 text-sm text-slate-300 md:grid-cols-4">
                <span>Prompts: {result.ai_usage_analysis.candidate_prompt_count}</span>
                <span>Responses: {result.ai_usage_analysis.assistant_response_count}</span>
                <span>File context: {result.ai_usage_analysis.prompts_with_file_context}</span>
                <span>Test runs: {result.ai_usage_analysis.test_run_count}</span>
              </div>
            </section>

            <PromptQuality result={result} />

            <AITranscript result={result} />

            <TelemetryTimeline result={result} />

            <section className="grid gap-4 rounded-md border border-slate-800 bg-slate-900/70 p-5">
              <h2 className="text-lg font-semibold">Candidate summary and tests</h2>
              <div className="grid gap-4 lg:grid-cols-2">
                <pre className="max-h-72 overflow-auto whitespace-pre-wrap rounded-md border border-slate-800 bg-slate-950 p-3 text-sm leading-6 text-slate-300">
                  {result.notes || "No candidate summary provided."}
                </pre>
                <pre className="max-h-72 overflow-auto whitespace-pre-wrap rounded-md border border-slate-800 bg-slate-950 p-3 text-sm leading-6 text-slate-300">
                  {result.test_output || "No submitted test output."}
                </pre>
              </div>
            </section>

            <section className="grid gap-4">
              <h2 className="text-lg font-semibold">Agent reviews</h2>
              {result.agent_reviews.length ? (
                result.agent_reviews.map((review) => <AgentReviewCard key={review.id} review={review} />)
              ) : (
                <div className="rounded-md border border-slate-800 bg-slate-900/70 p-5 text-sm text-slate-400">
                  Run the agent review to evaluate this repo submission.
                </div>
              )}
            </section>
          </>
        ) : null}
      </section>
    </main>
  );
}

export default function ResultPage() {
  return (
    <ProtectedRoute>
      <ResultContent />
    </ProtectedRoute>
  );
}
