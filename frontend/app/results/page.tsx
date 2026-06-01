"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { AppShell } from "@/components/app/app-shell";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  StatCard,
  StatusBadge,
  formatDateTime,
  statusTone,
} from "@/components/app/page-primitives";
import { useAuth } from "@/components/auth/auth-provider";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { ApiError, getResultsDashboard } from "@/lib/api";
import type { ResultsDashboardItem } from "@/lib/types";

function scoreTone(score: number | null): string {
  if (score === null) {
    return "text-slate-500";
  }
  if (score >= 80) {
    return "text-emerald-300";
  }
  if (score >= 65) {
    return "text-cyan-300";
  }
  if (score >= 50) {
    return "text-amber-300";
  }
  return "text-red-300";
}

function recommendationLabel(value: string | null): string {
  return value ? value.replaceAll("_", " ") : "Pending review";
}

function ResultsDashboardContent() {
  const { token, user } = useAuth();
  const [items, setItems] = useState<ResultsDashboardItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const canReview = user?.role === "ADMIN" || user?.role === "INTERVIEWER";

  useEffect(() => {
    if (!token || !canReview) {
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    getResultsDashboard(token)
      .then(setItems)
      .catch((requestError: unknown) => {
        const message = requestError instanceof ApiError ? requestError.message : "Unable to load results dashboard.";
        setError(message);
      })
      .finally(() => setIsLoading(false));
  }, [canReview, token]);

  const reviewedItems = items.filter((item) => item.weighted_score !== null);
  const averageScore = reviewedItems.length
    ? Math.round(reviewedItems.reduce((sum, item) => sum + (item.weighted_score ?? 0), 0) / reviewedItems.length)
    : null;
  const pendingReviews = items.filter(
    (item) => ["submitted", "ready_for_review", "review_in_progress"].includes(item.status) && item.weighted_score === null,
  ).length;
  const statusData = useMemo(
    () =>
      ["invited", "started", "ready_for_review", "review_in_progress", "reviewed", "review_failed"].map((status) => ({
        status,
        count: items.filter((item) => item.status === status).length,
      })),
    [items],
  );
  const scoreData = useMemo(
    () =>
      items
        .filter((item) => item.weighted_score !== null)
        .slice(0, 10)
        .map((item) => ({
          name: item.candidate_name.split(" ")[0] || item.candidate_email,
          score: item.weighted_score,
        })),
    [items],
  );

  if (!canReview) {
    return (
      <AppShell>
        <PageHeader
          description="Results are available to admin and interviewer roles."
          eyebrow="Access"
          title="Results"
        />
        <div className="mt-6">
          <EmptyState description="Your current role cannot review interview results." title="Results unavailable" />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <PageHeader
        actions={
          <Link
            className="inline-flex h-10 w-fit items-center justify-center rounded-md border border-slate-700 px-4 text-sm font-medium text-slate-200 hover:border-cyan-500 hover:text-cyan-200"
            href="/interviews"
          >
            Interviews
          </Link>
        }
        description="Review organization interview sessions, scores, recommendations, and risk signals."
        eyebrow="Hiring intelligence"
        title="Results"
      />

      <section className="mt-6 grid gap-5">
        {error ? <ErrorState message={error} /> : null}
        {isLoading ? <LoadingState label="Loading results..." /> : null}

        <section className="grid gap-3 md:grid-cols-4">
          <StatCard description="All candidate sessions." label="Sessions" value={items.length} />
          <StatCard description="Agent review completed." label="Reviewed" tone="success" value={items.filter((item) => item.status === "reviewed").length} />
          <StatCard description="Across reviewed sessions." label="Average score" value={averageScore ?? "--"} />
          <StatCard description="Submitted sessions awaiting review." label="Pending reviews" tone="warning" value={pendingReviews} />
        </section>

        {!isLoading && items.length === 0 ? (
          <EmptyState
            actionHref="/interviews"
            actionLabel="Create interview"
            description="Results will appear after candidates submit interview sessions."
            title="No results yet"
          />
        ) : null}

        {items.length ? (
          <>
            <section className="grid gap-4 lg:grid-cols-2">
              <div className="rounded-md border border-slate-800 bg-slate-900/70 p-5">
                <h2 className="text-lg font-semibold">Session status</h2>
                <div className="mt-4 h-64">
                  <ResponsiveContainer height="100%" width="100%">
                    <BarChart data={statusData}>
                      <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                      <XAxis dataKey="status" stroke="#94a3b8" />
                      <YAxis allowDecimals={false} stroke="#94a3b8" />
                      <Tooltip contentStyle={{ background: "#020617", border: "1px solid #334155", color: "#e2e8f0" }} />
                      <Bar dataKey="count" fill="#22c55e" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <div className="rounded-md border border-slate-800 bg-slate-900/70 p-5">
                <h2 className="text-lg font-semibold">Recent reviewed scores</h2>
                {scoreData.length ? (
                  <div className="mt-4 h-64">
                    <ResponsiveContainer height="100%" width="100%">
                      <BarChart data={scoreData}>
                        <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                        <XAxis dataKey="name" stroke="#94a3b8" />
                        <YAxis domain={[0, 100]} stroke="#94a3b8" />
                        <Tooltip contentStyle={{ background: "#020617", border: "1px solid #334155", color: "#e2e8f0" }} />
                        <Bar dataKey="score" fill="#06b6d4" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <p className="mt-4 rounded-md border border-slate-800 bg-slate-950 px-3 py-4 text-sm text-slate-400">
                    Scores appear after reviews are complete.
                  </p>
                )}
              </div>
            </section>

            <section className="rounded-md border border-slate-800 bg-slate-900/70">
              <div className="flex flex-col gap-2 border-b border-slate-800 px-5 py-4 md:flex-row md:items-center md:justify-between">
                <div>
                  <h2 className="text-lg font-semibold">Interview sessions</h2>
                  <p className="mt-1 text-sm text-slate-400">Only sessions in your organization are shown.</p>
                </div>
                <span className="text-xs uppercase tracking-wide text-slate-500">{items.length} total</span>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-800 text-left text-sm">
                  <thead className="bg-slate-950/60 text-xs uppercase tracking-wide text-slate-500">
                    <tr>
                      <th className="px-5 py-3 font-medium">Candidate</th>
                      <th className="px-5 py-3 font-medium">Interview</th>
                      <th className="px-5 py-3 font-medium">Status</th>
                      <th className="px-5 py-3 font-medium">Tests</th>
                      <th className="px-5 py-3 font-medium">Score</th>
                      <th className="px-5 py-3 font-medium">Recommendation</th>
                      <th className="px-5 py-3 font-medium">Submitted</th>
                      <th className="px-5 py-3 font-medium">Result</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {items.map((item) => (
                      <tr className="hover:bg-slate-950/60" key={item.session_id}>
                        <td className="px-5 py-4">
                          <p className="font-medium text-slate-100">{item.candidate_name}</p>
                          <p className="mt-1 text-xs text-slate-500">{item.candidate_email}</p>
                        </td>
                        <td className="max-w-xs px-5 py-4">
                          <p className="font-medium text-slate-200">{item.role_title}</p>
                          <p className="mt-1 truncate text-xs text-slate-500">{item.scenario_title ?? "Scenario pending"}</p>
                        </td>
                        <td className="px-5 py-4">
                          <StatusBadge label={item.status} tone={statusTone(item.status)} />
                        </td>
                        <td className="px-5 py-4">
                          {item.final_test_status ? (
                            <div className="grid gap-1">
                              <StatusBadge
                                label={item.final_test_status}
                                tone={item.final_test_status === "passed" ? "success" : "warning"}
                              />
                              <span className="text-xs text-slate-500">{item.test_attempt_count} run{item.test_attempt_count === 1 ? "" : "s"}</span>
                            </div>
                          ) : (
                            <span className="text-slate-600">Not run</span>
                          )}
                        </td>
                        <td className={`px-5 py-4 text-lg font-semibold ${scoreTone(item.weighted_score)}`}>
                          {item.weighted_score ?? "--"}
                        </td>
                        <td className="px-5 py-4 text-slate-300">{recommendationLabel(item.recommendation)}</td>
                        <td className="px-5 py-4 text-slate-400">{formatDateTime(item.submitted_at)}</td>
                        <td className="px-5 py-4">
                          {item.submission_id ? (
                            <Link className="font-medium text-cyan-300 hover:text-cyan-200" href={`/results/${item.session_id}`}>
                              View detail
                            </Link>
                          ) : (
                            <span className="text-slate-600">Pending</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        ) : null}
      </section>
    </AppShell>
  );
}

export default function ResultsDashboardPage() {
  return (
    <ProtectedRoute>
      <ResultsDashboardContent />
    </ProtectedRoute>
  );
}
