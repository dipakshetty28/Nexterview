"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ErrorState, LoadingState, StatusBadge, statusTone } from "@/components/app/page-primitives";
import { useAuth } from "@/components/auth/auth-provider";
import { Button } from "@/components/ui/button";
import { ApiError, getInvite, startInviteSession } from "@/lib/api";
import type { PublicInvite } from "@/lib/types";

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function InvitePage() {
  const params = useParams<{ token: string }>();
  const router = useRouter();
  const { isLoading: isAuthLoading, token: authToken, user } = useAuth();
  const inviteToken = params.token;
  const [invite, setInvite] = useState<PublicInvite | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!inviteToken) {
      return;
    }

    setIsLoading(true);
    getInvite(inviteToken)
      .then(setInvite)
      .catch((requestError: unknown) => {
        const message = requestError instanceof ApiError ? requestError.message : "Unable to load invite.";
        setError(message);
      })
      .finally(() => setIsLoading(false));
  }, [inviteToken]);

  async function handleStart() {
    if (!authToken || !inviteToken) {
      return;
    }

    setError(null);
    setIsStarting(true);
    try {
      const session = await startInviteSession(authToken, inviteToken);
      router.push(`/sessions/${session.id}`);
    } catch (requestError: unknown) {
      const message = requestError instanceof ApiError ? requestError.message : "Unable to start interview.";
      setError(message);
    } finally {
      setIsStarting(false);
    }
  }

  const loginHref = `/login?next=${encodeURIComponent(`/invite/${inviteToken}`)}`;
  const isExpectedCandidate = Boolean(
    invite &&
      user?.role === "CANDIDATE" &&
      invite.interview.is_ready &&
      (!invite.candidate_email || user.email === invite.candidate_email),
  );

  return (
    <main className="min-h-screen bg-slate-950 px-6 py-10 text-slate-100">
      <section className="mx-auto grid max-w-4xl gap-6">
        <div>
          <Link className="text-sm font-semibold text-cyan-300 hover:text-cyan-200" href="/">
            Nexterview
          </Link>
          <h1 className="mt-4 text-3xl font-semibold tracking-tight">Candidate invite</h1>
        </div>

        <div className="rounded-md border border-slate-800 bg-slate-900/60 p-6">
          {isLoading ? <LoadingState label="Loading candidate invite" rows={2} /> : null}
          {error ? <ErrorState message={error} /> : null}
          {invite ? (
            <div className="grid gap-5">
              <div>
                <p className="text-sm text-slate-400">Invited candidate</p>
                <p className="mt-1 font-medium">{invite.candidate_name || invite.candidate_email || "Any candidate in the organization"}</p>
                {invite.candidate_email ? <p className="mt-1 text-sm text-slate-500">{invite.candidate_email}</p> : null}
              </div>
              <div>
                <h2 className="text-2xl font-semibold">{invite.interview.role_title}</h2>
                <p className="mt-2 text-sm text-slate-400">
                  {invite.interview.seniority} / {invite.interview.difficulty} / {invite.interview.duration_minutes} minutes
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {invite.interview.stack.map((item) => (
                    <span className="rounded-full bg-slate-950 px-3 py-1 text-xs text-slate-300" key={item}>
                      {item}
                    </span>
                  ))}
                </div>
              </div>
              <div className="grid gap-2 text-sm text-slate-300 sm:grid-cols-3">
                <div className="rounded-md border border-slate-800 bg-slate-950 p-3">
                  <p className="text-slate-500">AI mode</p>
                  <p className="mt-1">{invite.interview.allowed_ai_mode}</p>
                </div>
                <div className="rounded-md border border-slate-800 bg-slate-950 p-3">
                  <p className="text-slate-500">Status</p>
                  <div className="mt-2">
                    <StatusBadge label={invite.status} tone={statusTone(invite.status)} />
                  </div>
                </div>
                <div className="rounded-md border border-slate-800 bg-slate-950 p-3">
                  <p className="text-slate-500">Scenario</p>
                  <div className="mt-2">
                    <StatusBadge label={invite.interview.scenario_status ?? "draft"} tone={statusTone(invite.interview.scenario_status)} />
                  </div>
                </div>
                <div className="rounded-md border border-slate-800 bg-slate-950 p-3">
                  <p className="text-slate-500">Expires</p>
                  <p className="mt-1">{formatDate(invite.expires_at)}</p>
                </div>
              </div>
              {invite.interview.scenario_title ? (
                <p className="rounded-md border border-slate-800 bg-slate-950 p-4 text-sm text-slate-300">
                  {invite.interview.scenario_title}
                </p>
              ) : null}

              {!invite.interview.is_ready ? (
                <p className="rounded-md border border-amber-900/70 bg-amber-950/40 px-3 py-2 text-sm text-amber-100">
                  This interview is not ready yet. The scenario is waiting for interviewer approval.
                </p>
              ) : null}

              {!isAuthLoading && !user && invite.interview.is_ready ? (
                <Link
                  className="inline-flex h-11 w-fit items-center justify-center rounded-md bg-cyan-400 px-4 text-sm font-medium text-slate-950 transition hover:bg-cyan-300"
                  href={loginHref}
                >
                  Log in to start
                </Link>
              ) : null}
              {!isAuthLoading && user && invite.interview.is_ready && !isExpectedCandidate ? (
                <p className="rounded-md border border-amber-900/70 bg-amber-950/40 px-3 py-2 text-sm text-amber-100">
                  {invite.candidate_email
                    ? `This invite is assigned to ${invite.candidate_email}. Log in with that candidate account to start.`
                    : "Log in with a candidate account in the invited organization to start."}
                </p>
              ) : null}
              {isExpectedCandidate ? (
                <Button aria-busy={isStarting} disabled={isStarting} onClick={() => void handleStart()} type="button">
                  {isStarting ? "Starting..." : invite.status === "used" ? "Continue interview" : "Start interview"}
                </Button>
              ) : null}
            </div>
          ) : null}
        </div>
      </section>
    </main>
  );
}
