"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { AppShell } from "@/components/app/app-shell";
import {
  ActionButton,
  EmptyState,
  ErrorState,
  InfoTooltip,
  LoadingState,
  PageHeader,
  SectionHeader,
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
    return "text-slate-400";
  }
  if (score >= 80) {
    return "text-emerald-700";
  }
  if (score >= 65) {
    return "text-blue-700";
  }
  if (score >= 50) {
    return "text-amber-700";
  }
  return "text-rose-700";
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
          <ActionButton href="/interviews" variant="secondary">
            Interviews
          </ActionButton>
        }
        description="Review organization interview sessions, scores, recommendations, and risk signals."
        eyebrow="Hiring intelligence"
        title="Results"
      />

      <section className="mt-6 grid gap-5">
        {error ? <ErrorState message={error} /> : null}
        {isLoading ? <LoadingState label="Loading results" rows={4} /> : null}

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
              <div className="rounded-card border border-white/80 bg-white p-5 shadow-panel">
                <SectionHeader
                  aside={<InfoTooltip content="Review status moves from submitted to reviewed as background or manual agents complete their work." label="Review status help" />}
                  title="Session status"
                />
                <div className="mt-4 h-64">
                  <ResponsiveContainer height="100%" width="100%">
                    <BarChart data={statusData}>
                      <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
                      <XAxis dataKey="status" stroke="#64748b" />
                      <YAxis allowDecimals={false} stroke="#64748b" />
                      <Tooltip contentStyle={{ background: "#ffffff", border: "1px solid #cbd5e1", color: "#0f172a", borderRadius: "12px" }} />
                      <Bar dataKey="count" fill="#059669" radius={[6, 6, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <div className="rounded-card border border-white/80 bg-white p-5 shadow-panel">
                <SectionHeader title="Recent reviewed scores" />
                {scoreData.length ? (
                  <div className="mt-4 h-64">
                    <ResponsiveContainer height="100%" width="100%">
                      <BarChart data={scoreData}>
                        <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
                        <XAxis dataKey="name" stroke="#64748b" />
                        <YAxis domain={[0, 100]} stroke="#64748b" />
                        <Tooltip contentStyle={{ background: "#ffffff", border: "1px solid #cbd5e1", color: "#0f172a", borderRadius: "12px" }} />
                        <Bar dataKey="score" fill="#2563eb" radius={[6, 6, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <p className="mt-4 rounded-lg border border-slate-200 bg-slate-50 px-3 py-4 text-sm text-slate-600">
                    Scores appear after reviews are complete.
                  </p>
                )}
              </div>
            </section>

            <section className="overflow-hidden rounded-card border border-white/80 bg-white shadow-panel">
              <div className="border-b border-slate-200 px-5 py-4">
                <SectionHeader
                  aside={<span className="text-xs uppercase tracking-wide text-slate-500">{items.length} total</span>}
                  description="Only sessions in your organization are shown."
                  title="Interview sessions"
                />
              </div>
              <div className="overflow-x-auto">
                <table className="table-surface">
                  <thead className="table-head">
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
                  <tbody className="divide-y divide-slate-200">
                    {items.map((item) => (
                      <tr className="table-row" key={item.session_id}>
                        <td className="px-5 py-4">
                          <p className="font-medium text-slate-950">{item.candidate_name}</p>
                          <p className="mt-1 text-xs text-slate-500">{item.candidate_email}</p>
                        </td>
                        <td className="max-w-xs px-5 py-4">
                          <p className="font-medium text-slate-800">{item.role_title}</p>
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
                            <span className="text-slate-400">Not run</span>
                          )}
                        </td>
                        <td className={`px-5 py-4 text-lg font-semibold ${scoreTone(item.weighted_score)}`}>
                          {item.weighted_score ?? "--"}
                        </td>
                        <td className="px-5 py-4 text-slate-700">{recommendationLabel(item.recommendation)}</td>
                        <td className="px-5 py-4 text-slate-600">{formatDateTime(item.submitted_at)}</td>
                        <td className="px-5 py-4">
                          {item.submission_id ? (
                            <Link className="font-semibold text-blue-700 hover:text-blue-900" href={`/results/${item.session_id}`}>
                              View detail
                            </Link>
                          ) : (
                            <span className="text-slate-400">Pending</span>
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
