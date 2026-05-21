"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ProtectedRoute } from "@/components/auth/protected-route";
import { useAuth } from "@/components/auth/auth-provider";
import { Button } from "@/components/ui/button";
import { deleteInterview, getInterview } from "@/lib/api";
import { aiModeOptions, difficultyOptions, interviewTypeOptions, optionLabel, seniorityOptions } from "@/lib/interview-options";
import type { Interview } from "@/lib/types";

function DetailItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-slate-800 bg-slate-950 p-4">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-2 font-medium text-slate-100">{value}</p>
    </div>
  );
}

function InterviewDetailContent() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { token } = useAuth();
  const [interview, setInterview] = useState<Interview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    if (!token || !params.id) {
      return;
    }

    getInterview(token, params.id)
      .then(setInterview)
      .catch(() => setError("Unable to load interview."));
  }, [params.id, token]);

  async function handleDelete() {
    if (!token || !interview) {
      return;
    }
    if (!window.confirm("Delete this interview?")) {
      return;
    }

    setIsDeleting(true);
    setError(null);
    try {
      await deleteInterview(token, interview.id);
      router.push("/dashboard");
    } catch {
      setError("Unable to delete interview.");
      setIsDeleting(false);
    }
  }

  if (error && !interview) {
    return (
      <main className="min-h-screen bg-slate-950 px-6 py-10 text-slate-100">
        <div className="mx-auto max-w-3xl rounded-md border border-slate-800 bg-slate-900/60 p-6">
          <h1 className="text-2xl font-semibold">Interview unavailable</h1>
          <p className="mt-3 text-sm leading-6 text-slate-400">{error}</p>
          <Link className="mt-6 inline-flex text-sm font-medium text-cyan-300 hover:text-cyan-200" href="/dashboard">
            Back to dashboard
          </Link>
        </div>
      </main>
    );
  }

  if (!interview) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 px-6 text-slate-300">
        <div className="h-10 w-10 rounded-full border-2 border-slate-800 border-t-cyan-400" aria-label="Loading" />
      </main>
    );
  }

  const scenario = interview.scenarios[0];

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-950/95">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-6 py-5 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <Link className="text-sm text-slate-400 hover:text-slate-200" href="/dashboard">
              Dashboard
            </Link>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight">{interview.title}</h1>
            <p className="mt-2 text-sm text-slate-400">{interview.organization.name}</p>
          </div>
          <Button variant="secondary" onClick={handleDelete} disabled={isDeleting}>
            {isDeleting ? "Deleting..." : "Delete"}
          </Button>
        </div>
      </header>
      <section className="mx-auto grid max-w-6xl gap-6 px-6 py-8">
        {error ? <p className="rounded-md border border-red-900/70 bg-red-950/50 px-3 py-2 text-sm text-red-200">{error}</p> : null}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <DetailItem label="Role" value={interview.role_title} />
          <DetailItem label="Seniority" value={optionLabel(seniorityOptions, interview.seniority)} />
          <DetailItem label="Type" value={optionLabel(interviewTypeOptions, interview.interview_type)} />
          <DetailItem label="Difficulty" value={optionLabel(difficultyOptions, interview.difficulty)} />
          <DetailItem label="Duration" value={`${interview.duration_minutes} minutes`} />
          <DetailItem label="AI mode" value={optionLabel(aiModeOptions, interview.ai_mode)} />
          <DetailItem label="Status" value={interview.status} />
          <DetailItem label="Sessions" value={String(interview.session_count)} />
        </div>
        <section className="rounded-md border border-slate-800 bg-slate-900/60 p-6">
          <h2 className="text-xl font-semibold">Stack</h2>
          <div className="mt-4 flex flex-wrap gap-2">
            {interview.stack.map((item) => (
              <span className="rounded-full border border-slate-700 px-3 py-1 text-sm text-slate-300" key={item}>
                {item}
              </span>
            ))}
          </div>
        </section>
        {scenario ? (
          <section className="rounded-md border border-slate-800 bg-slate-900/60 p-6">
            <h2 className="text-xl font-semibold">{scenario.title}</h2>
            <div className="mt-6 grid gap-5">
              <div>
                <p className="text-sm font-medium text-slate-300">Business context</p>
                <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-400">{scenario.business_context}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-slate-300">Candidate instructions</p>
                <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-400">{scenario.candidate_instructions}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-slate-300">Technical requirements</p>
                <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-400">{scenario.technical_requirements}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-slate-300">Evaluation rubric</p>
                <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-400">{scenario.evaluation_rubric}</p>
              </div>
            </div>
          </section>
        ) : null}
      </section>
    </main>
  );
}

export default function InterviewDetailPage() {
  return (
    <ProtectedRoute>
      <InterviewDetailContent />
    </ProtectedRoute>
  );
}
