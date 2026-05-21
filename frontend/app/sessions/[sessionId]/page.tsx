"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { useAuth } from "@/components/auth/auth-provider";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { Button } from "@/components/ui/button";
import {
  ApiError,
  getCandidateSession,
  runSessionTests,
  saveSessionEvent,
  submitSessionSolution,
} from "@/lib/api";
import type { CandidateSession, Submission, TestRunResult } from "@/lib/types";

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full min-h-96 items-center justify-center bg-slate-950 text-sm text-slate-400">
      Loading editor...
    </div>
  ),
});

function formatDuration(totalSeconds: number): string {
  const hours = Math.floor(totalSeconds / 3600)
    .toString()
    .padStart(2, "0");
  const minutes = Math.floor((totalSeconds % 3600) / 60)
    .toString()
    .padStart(2, "0");
  const seconds = Math.floor(totalSeconds % 60)
    .toString()
    .padStart(2, "0");
  return `${hours}:${minutes}:${seconds}`;
}

function formatSavedAt(value: string | null): string {
  if (!value) {
    return "Not saved yet";
  }
  return new Intl.DateTimeFormat(undefined, {
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

function languageForStack(stack: string[]): string {
  const joinedStack = stack.join(" ").toLowerCase();
  if (joinedStack.includes("python") || joinedStack.includes("fastapi")) {
    return "python";
  }
  if (joinedStack.includes("java") || joinedStack.includes("spring")) {
    return "java";
  }
  if (joinedStack.includes("c#") || joinedStack.includes(".net")) {
    return "csharp";
  }
  if (joinedStack.includes("go")) {
    return "go";
  }
  if (joinedStack.includes("react") || joinedStack.includes("next") || joinedStack.includes("node")) {
    return "typescript";
  }
  return "javascript";
}

function CandidateSessionContent() {
  const params = useParams<{ sessionId: string }>();
  const { token, user } = useAuth();
  const [session, setSession] = useState<CandidateSession | null>(null);
  const [code, setCode] = useState("");
  const [notes, setNotes] = useState("");
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isSavingCode, setIsSavingCode] = useState(false);
  const [isSavingNotes, setIsSavingNotes] = useState(false);
  const [isRunningTests, setIsRunningTests] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [lastSavedAt, setLastSavedAt] = useState<string | null>(null);
  const [testRun, setTestRun] = useState<TestRunResult | null>(null);
  const [submission, setSubmission] = useState<Submission | null>(null);
  const [error, setError] = useState<string | null>(null);
  const codeSaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const noteSaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const sessionStartedSent = useRef(false);

  useEffect(() => {
    if (!token || !params.sessionId) {
      return;
    }

    setIsLoading(true);
    setError(null);
    getCandidateSession(token, params.sessionId)
      .then((loadedSession) => {
        setSession(loadedSession);
        setCode(loadedSession.latest_code ?? loadedSession.scenario.starter_code);
        setNotes(loadedSession.notes ?? "");
        setLastSavedAt(loadedSession.last_autosaved_at);
        setSubmission(loadedSession.submission);

        if (!sessionStartedSent.current) {
          sessionStartedSent.current = true;
          void saveSessionEvent(token, loadedSession.id, { event_type: "session_started" }).catch(() => undefined);
        }
      })
      .catch((requestError: unknown) => {
        const message = requestError instanceof ApiError ? requestError.message : "Unable to load interview session.";
        setError(message);
      })
      .finally(() => setIsLoading(false));
  }, [params.sessionId, token]);

  useEffect(() => {
    if (!session?.started_at) {
      return;
    }

    const startedAt = new Date(session.started_at).getTime();
    const updateElapsedTime = () => {
      const nextElapsedSeconds = Math.max(0, Math.floor((new Date().getTime() - startedAt) / 1000));
      setElapsedSeconds(nextElapsedSeconds);
    };
    updateElapsedTime();
    const interval = window.setInterval(updateElapsedTime, 1000);
    return () => window.clearInterval(interval);
  }, [session?.started_at]);

  useEffect(() => {
    return () => {
      if (codeSaveTimer.current) {
        window.clearTimeout(codeSaveTimer.current);
      }
      if (noteSaveTimer.current) {
        window.clearTimeout(noteSaveTimer.current);
      }
    };
  }, []);

  const isSubmitted = session?.status === "submitted" || session?.status === "reviewed";

  function queueCodeAutosave(nextCode: string) {
    if (!token || !session || isSubmitted) {
      return;
    }
    if (codeSaveTimer.current) {
      window.clearTimeout(codeSaveTimer.current);
    }
    setIsSavingCode(true);
    codeSaveTimer.current = setTimeout(() => {
      saveSessionEvent(token, session.id, { event_type: "code_edit", payload: { code: nextCode } })
        .then((event) => {
          setLastSavedAt(String(event.payload.autosaved_at ?? event.created_at));
          setError(null);
        })
        .catch((requestError: unknown) => {
          const message = requestError instanceof ApiError ? requestError.message : "Unable to autosave code.";
          setError(message);
        })
        .finally(() => setIsSavingCode(false));
    }, 900);
  }

  function queueNotesAutosave(nextNotes: string) {
    if (!token || !session || isSubmitted) {
      return;
    }
    if (noteSaveTimer.current) {
      window.clearTimeout(noteSaveTimer.current);
    }
    setIsSavingNotes(true);
    noteSaveTimer.current = setTimeout(() => {
      saveSessionEvent(token, session.id, { event_type: "note_updated", payload: { notes: nextNotes } })
        .then((event) => {
          setLastSavedAt(String(event.payload.autosaved_at ?? event.created_at));
          setError(null);
        })
        .catch((requestError: unknown) => {
          const message = requestError instanceof ApiError ? requestError.message : "Unable to autosave notes.";
          setError(message);
        })
        .finally(() => setIsSavingNotes(false));
    }, 900);
  }

  function handleCodeChange(value: string | undefined) {
    const nextCode = value ?? "";
    setCode(nextCode);
    queueCodeAutosave(nextCode);
  }

  function handleNotesChange(value: string) {
    setNotes(value);
    queueNotesAutosave(value);
  }

  async function handleRunTests() {
    if (!token || !session) {
      return;
    }

    setIsRunningTests(true);
    setError(null);
    try {
      const result = await runSessionTests(token, session.id, { code });
      setTestRun(result);
      setLastSavedAt(new Date().toISOString());
    } catch (requestError: unknown) {
      const message = requestError instanceof ApiError ? requestError.message : "Unable to run simulated tests.";
      setError(message);
    } finally {
      setIsRunningTests(false);
    }
  }

  async function handleSubmit() {
    if (!token || !session) {
      return;
    }

    setIsSubmitting(true);
    setError(null);
    if (codeSaveTimer.current) {
      window.clearTimeout(codeSaveTimer.current);
      setIsSavingCode(false);
    }
    if (noteSaveTimer.current) {
      window.clearTimeout(noteSaveTimer.current);
      setIsSavingNotes(false);
    }
    try {
      const createdSubmission = await submitSessionSolution(token, session.id, {
        code,
        notes,
        test_output: testRun?.output ?? null,
      });
      setSubmission(createdSubmission);
      setSession({
        ...session,
        status: "submitted",
        submitted_at: createdSubmission.submitted_at,
        latest_code: createdSubmission.code,
        notes: createdSubmission.notes,
        submission: createdSubmission,
      });
      setLastSavedAt(createdSubmission.submitted_at);
    } catch (requestError: unknown) {
      const message = requestError instanceof ApiError ? requestError.message : "Unable to submit final solution.";
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-950/95 px-6 py-4">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <Link className="text-sm font-semibold text-cyan-300 hover:text-cyan-200" href="/">
              Nexterview
            </Link>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight">
              {session?.scenario.title ?? "Candidate interview room"}
            </h1>
            <p className="mt-1 text-sm text-slate-400">{user?.email}</p>
          </div>
          <div className="flex flex-wrap items-center gap-3 text-sm">
            <span className="rounded-md border border-slate-700 px-3 py-2 font-mono text-slate-200">
              {formatDuration(elapsedSeconds)}
            </span>
            <span className="rounded-md border border-slate-700 px-3 py-2 text-slate-300">
              {session?.status ?? "loading"}
            </span>
            <span className="rounded-md border border-slate-700 px-3 py-2 text-slate-400">
              Saved {formatSavedAt(lastSavedAt)}
            </span>
          </div>
        </div>
      </header>

      <section className="mx-auto grid max-w-7xl gap-4 px-6 py-5 lg:grid-cols-[320px_minmax(0,1fr)_320px]">
        {isLoading ? (
          <div className="lg:col-span-3 rounded-md border border-slate-800 bg-slate-900/70 p-6 text-slate-300">
            Loading interview room...
          </div>
        ) : null}

        {error ? (
          <p className="lg:col-span-3 rounded-md border border-red-900/70 bg-red-950/50 px-3 py-2 text-sm text-red-200">
            {error}
          </p>
        ) : null}

        {session ? (
          <>
            <aside className="grid content-start gap-4">
              <section className="rounded-md border border-slate-800 bg-slate-900/70 p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">Task</p>
                <h2 className="mt-2 text-lg font-semibold">{session.interview.role_title}</h2>
                <p className="mt-2 text-sm leading-6 text-slate-300">{session.scenario.business_context}</p>
                <div className="mt-4 flex flex-wrap gap-2">
                  {session.interview.stack.map((item) => (
                    <span className="rounded-md bg-slate-950 px-2.5 py-1 text-xs text-slate-300" key={item}>
                      {item}
                    </span>
                  ))}
                </div>
              </section>

              <section className="rounded-md border border-slate-800 bg-slate-900/70 p-4">
                <h3 className="text-sm font-semibold text-slate-100">Requirements</h3>
                <ul className="mt-3 grid gap-2 text-sm leading-6 text-slate-300">
                  {session.scenario.technical_requirements.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </section>

              <section className="rounded-md border border-slate-800 bg-slate-900/70 p-4">
                <h3 className="text-sm font-semibold text-slate-100">Expected behavior</h3>
                <ul className="mt-3 grid gap-2 text-sm leading-6 text-slate-300">
                  {session.scenario.expected_behavior.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </section>

              <section className="rounded-md border border-slate-800 bg-slate-900/70 p-4">
                <h3 className="text-sm font-semibold text-slate-100">Logs or bug report</h3>
                <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap text-xs leading-5 text-slate-300">
                  {session.scenario.logs_or_bug_report}
                </pre>
              </section>
            </aside>

            <section className="grid min-h-[720px] grid-rows-[auto_minmax(420px,1fr)_auto] overflow-hidden rounded-md border border-slate-800 bg-slate-900/70">
              <div className="flex flex-col gap-3 border-b border-slate-800 p-4 md:flex-row md:items-center md:justify-between">
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-500">Editor</p>
                  <p className="mt-1 text-sm text-slate-300">
                    {isSavingCode ? "Saving code..." : isSubmitted ? "Final code locked" : "Autosaves after edits"}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button disabled={isRunningTests || isSubmitted} onClick={() => void handleRunTests()} type="button">
                    {isRunningTests ? "Running..." : "Run simulated tests"}
                  </Button>
                  <Button disabled={isSubmitting || isSubmitted || code.trim().length === 0} onClick={() => void handleSubmit()} type="button">
                    {isSubmitting ? "Submitting..." : isSubmitted ? "Submitted" : "Submit final"}
                  </Button>
                </div>
              </div>
              <div className="min-h-0">
                <MonacoEditor
                  height="100%"
                  language={languageForStack(session.interview.stack)}
                  onChange={handleCodeChange}
                  options={{
                    automaticLayout: true,
                    fontSize: 13,
                    minimap: { enabled: false },
                    readOnly: isSubmitted,
                    scrollBeyondLastLine: false,
                    wordWrap: "on",
                  }}
                  theme="vs-dark"
                  value={code}
                />
              </div>
              <section className="border-t border-slate-800 p-4">
                <h3 className="text-sm font-semibold text-slate-100">Test run simulation</h3>
                {testRun ? (
                  <div className="mt-3 grid gap-3">
                    <p className={testRun.status === "passed" ? "text-sm text-emerald-300" : "text-sm text-amber-300"}>
                      {testRun.output}
                    </p>
                    <div className="grid gap-2">
                      {testRun.cases.map((testCase) => (
                        <div className="rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm" key={testCase.name}>
                          <div className="flex items-center justify-between gap-3">
                            <span className="font-medium text-slate-200">{testCase.name}</span>
                            <span className={testCase.status === "passed" ? "text-emerald-300" : "text-amber-300"}>
                              {testCase.status}
                            </span>
                          </div>
                          <p className="mt-1 text-slate-400">{testCase.details}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <p className="mt-2 text-sm text-slate-400">Run the simulated checks when you want feedback on the current code snapshot.</p>
                )}
              </section>
            </section>

            <aside className="grid content-start gap-4">
              <section className="rounded-md border border-slate-800 bg-slate-900/70 p-4">
                <h3 className="text-sm font-semibold text-slate-100">AI copilot</h3>
                <div className="mt-3 rounded-md border border-slate-800 bg-slate-950 p-3 text-sm leading-6 text-slate-300">
                  Copilot chat will land in a later PR. For now, use your normal AI workflow and capture decisions in notes.
                </div>
                <textarea
                  className="mt-3 min-h-24 w-full resize-none rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-500 outline-none"
                  disabled
                  placeholder="Copilot prompt placeholder"
                />
              </section>

              <section className="rounded-md border border-slate-800 bg-slate-900/70 p-4">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="text-sm font-semibold text-slate-100">Root cause / notes</h3>
                  <span className="text-xs text-slate-500">{isSavingNotes ? "Saving..." : "Autosaved"}</span>
                </div>
                <textarea
                  className="mt-3 min-h-64 w-full resize-y rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm leading-6 text-slate-200 outline-none focus:border-cyan-500"
                  disabled={isSubmitted}
                  onChange={(event) => handleNotesChange(event.target.value)}
                  placeholder="Explain the root cause, tradeoffs, validation steps, and what you changed."
                  value={notes}
                />
              </section>

              <section className="rounded-md border border-slate-800 bg-slate-900/70 p-4">
                <h3 className="text-sm font-semibold text-slate-100">Candidate instructions</h3>
                <p className="mt-3 text-sm leading-6 text-slate-300">{session.scenario.candidate_instructions}</p>
              </section>

              {submission ? (
                <section className="rounded-md border border-emerald-900/70 bg-emerald-950/30 p-4">
                  <h3 className="text-sm font-semibold text-emerald-100">Submission received</h3>
                  <p className="mt-2 text-sm leading-6 text-emerald-200">
                    Your final solution was submitted at {formatSavedAt(submission.submitted_at)}.
                  </p>
                </section>
              ) : null}
            </aside>
          </>
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
