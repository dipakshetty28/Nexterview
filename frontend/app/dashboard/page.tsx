"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/app/app-shell";
import {
  ActionButton,
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  SectionHeader,
  StatCard,
  StatusBadge,
  formatDateTime,
  statusTone,
} from "@/components/app/page-primitives";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { useAuth } from "@/components/auth/auth-provider";
import { ApiError, getDashboard, getInterviews, getResultsDashboard } from "@/lib/api";
import type { DashboardResponse, Interview, ResultsDashboardItem } from "@/lib/types";

function averageScore(items: ResultsDashboardItem[]): number | null {
  const scored = items.filter((item) => item.weighted_score !== null);
  if (!scored.length) {
    return null;
  }
  return Math.round(scored.reduce((sum, item) => sum + (item.weighted_score ?? 0), 0) / scored.length);
}

function mostRecentTimestamp(item: ResultsDashboardItem): number {
  return Date.parse(item.reviewed_at ?? item.submitted_at ?? "") || 0;
}

function DashboardContent() {
  const { token, user } = useAuth();
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [interviews, setInterviews] = useState<Interview[]>([]);
  const [sessions, setSessions] = useState<ResultsDashboardItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const canManage = user?.role === "ADMIN" || user?.role === "INTERVIEWER";

  useEffect(() => {
    if (!token) {
      return;
    }

    setIsLoading(true);
    setError(null);
    Promise.all([
      getDashboard(token),
      canManage ? getInterviews(token) : Promise.resolve([]),
      canManage ? getResultsDashboard(token) : Promise.resolve([]),
    ])
      .then(([loadedDashboard, loadedInterviews, loadedSessions]) => {
        setDashboard(loadedDashboard);
        setInterviews(loadedInterviews);
        setSessions(loadedSessions);
      })
      .catch((requestError: unknown) => {
        const message = requestError instanceof ApiError ? requestError.message : "Unable to load dashboard.";
        setError(message);
      })
      .finally(() => setIsLoading(false));
  }, [canManage, token]);

  const metrics = useMemo(() => {
    const activeInterviews = interviews.filter((interview) => interview.status !== "ARCHIVED").length;
    const completedSessions = sessions.filter((session) =>
      ["submitted", "ready_for_review", "review_in_progress", "reviewed", "review_failed"].includes(session.status),
    ).length;
    const pendingReviews = sessions.filter(
      (session) => ["submitted", "ready_for_review", "review_in_progress"].includes(session.status) && session.weighted_score === null,
    ).length;
    return {
      activeInterviews,
      completedSessions,
      pendingReviews,
      averageScore: averageScore(sessions),
    };
  }, [interviews, sessions]);

  const recentSessions = useMemo(
    () => [...sessions].sort((first, second) => mostRecentTimestamp(second) - mostRecentTimestamp(first)).slice(0, 6),
    [sessions],
  );

  if (!canManage) {
    return (
      <AppShell>
        <PageHeader
          description="Candidate interview sessions open from invite links. Interviewer and admin workspace access is restricted by role."
          eyebrow="Workspace"
          title="Dashboard"
        />
        <div className="mt-6">
          <EmptyState
            description="Your account is not assigned to interviewer or admin management pages."
            title="No hiring workspace access"
          />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <PageHeader
        actions={
          <ActionButton href="/interviews">
            Create interview
          </ActionButton>
        }
        description="Monitor interview activity, review readiness, and candidate outcomes for your organization."
        eyebrow={dashboard?.organizations[0]?.organization.name ?? "Hiring workspace"}
        title="Dashboard"
      />

      <div className="mt-6 grid gap-5">
        {error ? <ErrorState message={error} /> : null}
        {isLoading ? <LoadingState label="Loading hiring workspace" rows={3} /> : null}

        <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard description="Configured interviews in this organization." label="Active interviews" tone="info" value={metrics.activeInterviews} />
          <StatCard description="Submitted or reviewed candidate sessions." label="Completed sessions" tone="success" value={metrics.completedSessions} />
          <StatCard description="Submitted sessions waiting for review." label="Pending reviews" tone="warning" value={metrics.pendingReviews} />
          <StatCard description="Across reviewed sessions." label="Average score" value={metrics.averageScore ?? "--"} />
        </section>

        {!isLoading && interviews.length === 0 && sessions.length === 0 ? (
          <EmptyState
            actionHref="/interviews"
            actionLabel="Create interview"
            description="Set up a role, generate a realistic scenario, and invite your first candidate."
            title="No interview activity yet"
          />
        ) : null}

        <section className="grid gap-4 overflow-hidden rounded-card border border-white/80 bg-white shadow-panel">
          <div className="border-b border-slate-200 px-5 py-4">
            <SectionHeader
              aside={
                <Link className="text-sm font-semibold text-blue-700 hover:text-blue-900" href="/results">
                  View all results
                </Link>
              }
              description="Latest submitted or reviewed sessions across your organization."
              title="Recent candidate sessions"
            />
          </div>

          {!isLoading && recentSessions.length === 0 ? (
            <div className="px-5 pb-5">
              <EmptyState
                actionHref="/interviews"
                actionLabel="Invite candidate"
                description="Candidate sessions will appear here after invites are created and candidates begin interviews."
                title="No candidate sessions yet"
              />
            </div>
          ) : null}

          {recentSessions.length ? (
            <div className="overflow-x-auto">
              <table className="table-surface">
                <thead className="table-head">
                  <tr>
                    <th className="px-5 py-3 font-medium">Candidate</th>
                    <th className="px-5 py-3 font-medium">Interview</th>
                    <th className="px-5 py-3 font-medium">Status</th>
                    <th className="px-5 py-3 font-medium">Score</th>
                    <th className="px-5 py-3 font-medium">Updated</th>
                    <th className="px-5 py-3 font-medium">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {recentSessions.map((session) => (
                    <tr className="table-row" key={session.session_id}>
                      <td className="px-5 py-4">
                        <p className="font-medium text-slate-950">{session.candidate_name}</p>
                        <p className="mt-1 text-xs text-slate-500">{session.candidate_email}</p>
                      </td>
                      <td className="max-w-xs px-5 py-4">
                        <p className="font-medium text-slate-800">{session.role_title}</p>
                        <p className="mt-1 truncate text-xs text-slate-500">{session.scenario_title ?? "Scenario pending"}</p>
                      </td>
                      <td className="px-5 py-4">
                        <StatusBadge label={session.status} tone={statusTone(session.status)} />
                      </td>
                      <td className="px-5 py-4 text-slate-800">{session.weighted_score ?? "--"}</td>
                      <td className="px-5 py-4 text-slate-600">{formatDateTime(session.reviewed_at ?? session.submitted_at)}</td>
                      <td className="px-5 py-4">
                        {session.submission_id ? (
                          <Link className="font-semibold text-blue-700 hover:text-blue-900" href={`/results/${session.session_id}`}>
                            Review
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
          ) : null}
        </section>
      </div>
    </AppShell>
  );
}

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  );
}
