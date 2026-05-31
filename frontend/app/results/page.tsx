"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { useAuth } from "@/components/auth/auth-provider";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { ApiError, getResultsDashboard } from "@/lib/api";
import type { ResultsDashboardItem } from "@/lib/types";

const STATUS_TONES: Record<ResultsDashboardItem["status"], string> = {
  invited: "border-slate-700 bg-slate-950 text-slate-300",
  started: "border-cyan-900/70 bg-cyan-950/30 text-cyan-200",
  submitted: "border-amber-900/70 bg-amber-950/30 text-amber-200",
  reviewed: "border-emerald-900/70 bg-emerald-950/30 text-emerald-200",
};

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

function formatDate(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "Not submitted";
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
  const statusData = useMemo(
    () =>
      ["invited", "started", "submitted", "reviewed"].map((status) => ({
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
      <main className="min-h-screen bg-slate-950 px-6 py-8 text-slate-100">
        <div className="mx-auto max-w-3xl rounded-md border border-slate-800 bg-slate-900/70 p-6">
          <h1 className="text-2xl font-semibold">Results dashboard</h1>
          <p className="mt-3 text-sm text-slate-400">Your role cannot review interview results.</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-950/95">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-6 py-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <Link className="text-sm font-medium text-cyan-300 hover:text-cyan-200" href="/dashboard">
              Back to dashboard
            </Link>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight">Results dashboard</h1>
            <p className="mt-1 text-sm text-slate-400">Review organization interview sessions, scores, and recommendations.</p>
          </div>
          <Link
            className="inline-flex h-10 w-fit items-center justify-center rounded-md border border-slate-700 px-4 text-sm font-medium text-slate-200 hover:border-cyan-500 hover:text-cyan-200"
            href="/interviews"
          >
            Interviews
          </Link>
        </div>
      </header>

      <section className="mx-auto grid max-w-7xl gap-5 px-6 py-8">
        {error ? (
          <p className="rounded-md border border-red-900/70 bg-red-950/50 px-3 py-2 text-sm text-red-200">{error}</p>
        ) : null}

        <section className="grid gap-3 md:grid-cols-4">
          <div className="rounded-md border border-slate-800 bg-slate-900/70 p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">Sessions</p>
            <p className="mt-2 text-2xl font-semibold">{items.length}</p>
          </div>
          <div className="rounded-md border border-slate-800 bg-slate-900/70 p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">Reviewed</p>
            <p className="mt-2 text-2xl font-semibold text-emerald-300">
              {items.filter((item) => item.status === "reviewed").length}
            </p>
          </div>
          <div className="rounded-md border border-slate-800 bg-slate-900/70 p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">Average score</p>
            <p className={`mt-2 text-2xl font-semibold ${scoreTone(averageScore)}`}>{averageScore ?? "--"}</p>
          </div>
          <div className="rounded-md border border-slate-800 bg-slate-900/70 p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">Open risks</p>
            <p className="mt-2 text-2xl font-semibold text-amber-300">
              {items.reduce((count, item) => count + item.risk_flags.length, 0)}
            </p>
          </div>
        </section>

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
          {isLoading ? <p className="px-5 py-5 text-sm text-slate-400">Loading results...</p> : null}
          {!isLoading && items.length === 0 ? <p className="px-5 py-5 text-sm text-slate-400">No sessions yet.</p> : null}
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-800 text-left text-sm">
              <thead className="bg-slate-950/60 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-5 py-3 font-medium">Candidate</th>
                  <th className="px-5 py-3 font-medium">Interview</th>
                  <th className="px-5 py-3 font-medium">Status</th>
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
                      <span className={`rounded-full border px-3 py-1 text-xs font-medium ${STATUS_TONES[item.status]}`}>
                        {item.status}
                      </span>
                    </td>
                    <td className={`px-5 py-4 text-lg font-semibold ${scoreTone(item.weighted_score)}`}>
                      {item.weighted_score ?? "--"}
                    </td>
                    <td className="px-5 py-4 text-slate-300">{recommendationLabel(item.recommendation)}</td>
                    <td className="px-5 py-4 text-slate-400">{formatDate(item.submitted_at)}</td>
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
      </section>
    </main>
  );
}

export default function ResultsDashboardPage() {
  return (
    <ProtectedRoute>
      <ResultsDashboardContent />
    </ProtectedRoute>
  );
}
