"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { ProtectedRoute } from "@/components/auth/protected-route";
import { useAuth } from "@/components/auth/auth-provider";
import { ApiError, getCandidateSession } from "@/lib/api";
import type { CandidateSession } from "@/lib/types";

function CandidateSessionContent() {
  const params = useParams<{ sessionId: string }>();
  const { token, user } = useAuth();
  const [session, setSession] = useState<CandidateSession | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token || !params.sessionId) {
      return;
    }

    setIsLoading(true);
    getCandidateSession(token, params.sessionId)
      .then(setSession)
      .catch((requestError: unknown) => {
        const message = requestError instanceof ApiError ? requestError.message : "Unable to load session.";
        setError(message);
      })
      .finally(() => setIsLoading(false));
  }, [params.sessionId, token]);

  return (
    <main className="min-h-screen bg-slate-950 px-6 py-10 text-slate-100">
      <section className="mx-auto grid max-w-5xl gap-6">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <Link className="text-sm font-semibold text-cyan-300 hover:text-cyan-200" href="/">
              Nexterview
            </Link>
            <h1 className="mt-4 text-3xl font-semibold tracking-tight">Interview session</h1>
            <p className="mt-2 text-sm text-slate-400">{user?.email}</p>
          </div>
          {session ? (
            <span className="w-fit rounded-full border border-slate-700 px-3 py-1 text-sm text-slate-300">
              {session.status}
            </span>
          ) : null}
        </header>

        {isLoading ? <div className="rounded-md border border-slate-800 bg-slate-900/60 p-6 text-slate-300">Loading session...</div> : null}
        {error ? <p className="rounded-md border border-red-900/70 bg-red-950/50 px-3 py-2 text-sm text-red-200">{error}</p> : null}

        {session ? (
          <div className="grid gap-6">
            <section className="rounded-md border border-slate-800 bg-slate-900/60 p-6">
              <p className="text-sm text-slate-400">{session.interview.interview_type}</p>
              <h2 className="mt-2 text-2xl font-semibold">{session.scenario.title}</h2>
              <p className="mt-3 text-sm leading-6 text-slate-300">{session.scenario.business_context}</p>
              <div className="mt-4 flex flex-wrap gap-2">
                {session.interview.stack.map((item) => (
                  <span className="rounded-full bg-slate-950 px-3 py-1 text-xs text-slate-300" key={item}>
                    {item}
                  </span>
                ))}
              </div>
            </section>

            <section className="rounded-md border border-slate-800 bg-slate-900/60 p-6">
              <h3 className="text-lg font-semibold">Candidate instructions</h3>
              <p className="mt-3 text-sm leading-6 text-slate-300">{session.scenario.candidate_instructions}</p>
            </section>

            <section className="grid gap-4 rounded-md border border-slate-800 bg-slate-900/60 p-6 lg:grid-cols-2">
              <div>
                <h3 className="text-lg font-semibold">Technical requirements</h3>
                <ul className="mt-3 grid gap-2 text-sm text-slate-300">
                  {session.scenario.technical_requirements.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
              <div>
                <h3 className="text-lg font-semibold">Expected behavior</h3>
                <ul className="mt-3 grid gap-2 text-sm text-slate-300">
                  {session.scenario.expected_behavior.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            </section>

            <section className="rounded-md border border-slate-800 bg-slate-900/60 p-6">
              <h3 className="text-lg font-semibold">Logs or bug report</h3>
              <pre className="mt-3 whitespace-pre-wrap rounded-md border border-slate-800 bg-slate-950 p-4 text-sm leading-6 text-slate-300">
                {session.scenario.logs_or_bug_report}
              </pre>
            </section>

            <section className="rounded-md border border-slate-800 bg-slate-900/60 p-6">
              <h3 className="text-lg font-semibold">Starter code</h3>
              <pre className="mt-3 max-h-96 overflow-auto rounded-md border border-slate-800 bg-slate-950 p-4 text-xs leading-5 text-slate-300">
                {session.scenario.starter_code}
              </pre>
            </section>
          </div>
        ) : null}
      </section>
    </main>
  );
}

export default function CandidateSessionPage() {
  return (
    <ProtectedRoute>
      <CandidateSessionContent />
    </ProtectedRoute>
  );
}
