"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { ProtectedRoute } from "@/components/auth/protected-route";
import { useAuth } from "@/components/auth/auth-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  ApiError,
  createCandidateInvite,
  createInterview,
  deleteInterview,
  generateScenario,
  getInterviews,
} from "@/lib/api";
import type { Interview, InterviewCreateInput, ProjectFile, ScenarioProject } from "@/lib/types";

const DEFAULT_CRITERIA = [
  "Correctness and edge-case handling",
  "Debugging process and verification discipline",
  "Code quality, maintainability, and error handling",
  "AI collaboration quality and ability to validate suggestions",
].join("\n");

type InterviewFormState = {
  role_title: string;
  seniority: string;
  stack: string;
  difficulty: string;
  interview_type: string;
  duration_minutes: string;
  allowed_ai_mode: string;
  evaluation_criteria: string;
};

const DEFAULT_FORM: InterviewFormState = {
  role_title: "Backend Platform Engineer",
  seniority: "Senior",
  stack: "Python, FastAPI, PostgreSQL, Redis, Docker",
  difficulty: "Intermediate",
  interview_type: "Backend debugging",
  duration_minutes: "75",
  allowed_ai_mode: "Pair Programmer Mode",
  evaluation_criteria: DEFAULT_CRITERIA,
};

const DEFAULT_INVITE_EMAIL = "candidate@nexterview.dev";

function splitCommaList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function splitLineList(value: string): string[] {
  return value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function toCreateInput(form: InterviewFormState): InterviewCreateInput {
  return {
    role_title: form.role_title,
    seniority: form.seniority,
    stack: splitCommaList(form.stack),
    difficulty: form.difficulty,
    interview_type: form.interview_type,
    duration_minutes: Number(form.duration_minutes),
    allowed_ai_mode: form.allowed_ai_mode,
    evaluation_criteria: splitLineList(form.evaluation_criteria),
  };
}

function fileTone(file: ProjectFile): string {
  if (file.is_hidden) {
    return "border-amber-900/60 bg-amber-950/20 text-amber-100";
  }
  if (!file.is_editable) {
    return "border-slate-700 bg-slate-950 text-slate-300";
  }
  return "border-cyan-900/50 bg-cyan-950/20 text-cyan-100";
}

function ProjectFilesPreview({ project }: { project: ScenarioProject }) {
  return (
    <section className="grid gap-3 rounded-md border border-slate-800 bg-slate-950/50 p-4">
      <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
        <div>
          <h4 className="text-sm font-semibold text-slate-100">{project.project_name}</h4>
          <p className="mt-1 text-xs text-slate-500">
            {project.framework ?? "Project"} / {project.package_manager ?? "package manager"} / {project.files.length} files
          </p>
        </div>
        <div className="grid gap-1 text-xs text-slate-400 md:text-right">
          {project.install_command ? <span>Install: {project.install_command}</span> : null}
          {project.run_command ? <span>Run: {project.run_command}</span> : null}
          {project.test_command ? <span>Test: {project.test_command}</span> : null}
        </div>
      </div>
      <div className="grid gap-2">
        {project.files.map((file) => (
          <details className={`rounded-md border ${fileTone(file)}`} key={file.path}>
            <summary className="cursor-pointer px-3 py-2 text-sm font-medium">
              <span>{file.path}</span>
              <span className="ml-2 text-xs opacity-70">
                {file.language} / {file.file_type}
                {file.is_hidden ? " / hidden" : ""}
              </span>
            </summary>
            <pre className="max-h-80 overflow-auto border-t border-inherit bg-slate-950 p-3 text-xs leading-5 text-slate-200">
              {file.content}
            </pre>
          </details>
        ))}
      </div>
    </section>
  );
}

function InterviewsContent() {
  const { logout, token, user } = useAuth();
  const [form, setForm] = useState<InterviewFormState>(DEFAULT_FORM);
  const [interviews, setInterviews] = useState<Interview[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [generatingId, setGeneratingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [inviteEmails, setInviteEmails] = useState<Record<string, string>>({});
  const [inviteGeneratingId, setInviteGeneratingId] = useState<string | null>(null);
  const [inviteLinks, setInviteLinks] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  const canManageInterviews = user?.role === "ADMIN" || user?.role === "INTERVIEWER";
  const sortedInterviews = useMemo(
    () => [...interviews].sort((first, second) => Date.parse(second.created_at) - Date.parse(first.created_at)),
    [interviews],
  );

  useEffect(() => {
    if (!token || !canManageInterviews) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    getInterviews(token)
      .then(setInterviews)
      .catch((requestError: unknown) => {
        const message = requestError instanceof ApiError ? requestError.message : "Unable to load interviews.";
        setError(message);
      })
      .finally(() => setIsLoading(false));
  }, [canManageInterviews, token]);

  function updateField(field: keyof InterviewFormState, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function updateInviteEmail(interviewId: string, value: string) {
    setInviteEmails((current) => ({ ...current, [interviewId]: value }));
  }

  async function handleCreateInterview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) {
      return;
    }

    setError(null);
    setIsCreating(true);
    try {
      const created = await createInterview(token, toCreateInput(form));
      setInterviews((current) => [created, ...current]);
      setInviteEmails((current) => ({ ...current, [created.id]: DEFAULT_INVITE_EMAIL }));
    } catch (requestError: unknown) {
      const message = requestError instanceof ApiError ? requestError.message : "Unable to create interview.";
      setError(message);
    } finally {
      setIsCreating(false);
    }
  }

  async function handleGenerateScenario(interviewId: string) {
    if (!token) {
      return;
    }

    setError(null);
    setGeneratingId(interviewId);
    try {
      const scenario = await generateScenario(token, interviewId);
      setInterviews((current) =>
        current.map((interview) =>
          interview.id === interviewId ? { ...interview, scenario, status: "READY" } : interview,
        ),
      );
    } catch (requestError: unknown) {
      const message = requestError instanceof ApiError ? requestError.message : "Unable to generate scenario.";
      setError(message);
    } finally {
      setGeneratingId(null);
    }
  }

  async function handleCreateInvite(interviewId: string) {
    if (!token) {
      return;
    }

    const candidateEmail = (inviteEmails[interviewId] ?? DEFAULT_INVITE_EMAIL).trim();
    if (!candidateEmail) {
      setError("Enter a candidate email before generating an invite.");
      return;
    }

    setError(null);
    setInviteGeneratingId(interviewId);
    try {
      const invite = await createCandidateInvite(token, interviewId, { candidate_email: candidateEmail });
      setInviteLinks((current) => ({ ...current, [interviewId]: invite.invite_url }));
    } catch (requestError: unknown) {
      const message = requestError instanceof ApiError ? requestError.message : "Unable to create invite.";
      setError(message);
    } finally {
      setInviteGeneratingId(null);
    }
  }

  async function handleDeleteInterview(interview: Interview) {
    if (!token) {
      return;
    }
    const confirmed = window.confirm(`Delete "${interview.role_title}" and all generated scenario/session data?`);
    if (!confirmed) {
      return;
    }

    setError(null);
    setDeletingId(interview.id);
    try {
      await deleteInterview(token, interview.id);
      setInterviews((current) => current.filter((item) => item.id !== interview.id));
      setInviteLinks((current) => {
        const next = { ...current };
        delete next[interview.id];
        return next;
      });
      setInviteEmails((current) => {
        const next = { ...current };
        delete next[interview.id];
        return next;
      });
    } catch (requestError: unknown) {
      const message = requestError instanceof ApiError ? requestError.message : "Unable to delete interview.";
      setError(message);
    } finally {
      setDeletingId(null);
    }
  }

  if (!canManageInterviews) {
    return (
      <main className="min-h-screen bg-slate-950 px-6 py-8 text-slate-100">
        <div className="mx-auto max-w-3xl rounded-md border border-slate-800 bg-slate-900/60 p-6">
          <p className="text-sm text-slate-400">Nexterview</p>
          <h1 className="mt-2 text-2xl font-semibold">Interviews</h1>
          <p className="mt-4 text-slate-300">Your role cannot manage interviews.</p>
          <Link className="mt-5 inline-flex text-sm font-medium text-cyan-300 hover:text-cyan-200" href="/dashboard">
            Back to dashboard
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-950/95">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
          <div>
            <p className="text-sm text-slate-400">Nexterview</p>
            <h1 className="text-2xl font-semibold tracking-tight">Interview management</h1>
          </div>
          <div className="flex items-center gap-3">
            <Link className="text-sm font-medium text-slate-300 hover:text-white" href="/dashboard">
              Dashboard
            </Link>
            <Button variant="secondary" onClick={logout}>
              Log out
            </Button>
          </div>
        </div>
      </header>

      <section className="mx-auto grid max-w-6xl gap-6 px-6 py-8 lg:grid-cols-[380px_1fr]">
        <form className="grid gap-4 rounded-md border border-slate-800 bg-slate-900/60 p-5" onSubmit={handleCreateInterview}>
          <div>
            <h2 className="text-lg font-semibold">Create interview</h2>
            <p className="mt-1 text-sm text-slate-400">Configure the role, stack, and evaluation signals.</p>
          </div>
          <Input
            id="role_title"
            label="Role title"
            value={form.role_title}
            onChange={(event) => updateField("role_title", event.target.value)}
            required
          />
          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              id="seniority"
              label="Seniority"
              value={form.seniority}
              onChange={(event) => updateField("seniority", event.target.value)}
              required
            />
            <Input
              id="difficulty"
              label="Difficulty"
              value={form.difficulty}
              onChange={(event) => updateField("difficulty", event.target.value)}
              required
            />
          </div>
          <Input
            id="interview_type"
            label="Interview type"
            value={form.interview_type}
            onChange={(event) => updateField("interview_type", event.target.value)}
            required
          />
          <Input
            id="stack"
            label="Stack"
            value={form.stack}
            onChange={(event) => updateField("stack", event.target.value)}
            required
          />
          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              id="duration_minutes"
              label="Duration minutes"
              min={30}
              max={240}
              type="number"
              value={form.duration_minutes}
              onChange={(event) => updateField("duration_minutes", event.target.value)}
              required
            />
            <Input
              id="allowed_ai_mode"
              label="Allowed AI mode"
              value={form.allowed_ai_mode}
              onChange={(event) => updateField("allowed_ai_mode", event.target.value)}
              required
            />
          </div>
          <label className="grid gap-2 text-sm text-slate-200" htmlFor="evaluation_criteria">
            <span>Evaluation criteria</span>
            <textarea
              className="min-h-32 rounded-md border border-slate-700 bg-slate-950 px-3 py-3 text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/20"
              id="evaluation_criteria"
              value={form.evaluation_criteria}
              onChange={(event) => updateField("evaluation_criteria", event.target.value)}
              required
            />
          </label>
          {error ? <p className="rounded-md border border-red-900/70 bg-red-950/50 px-3 py-2 text-sm text-red-200">{error}</p> : null}
          <Button disabled={isCreating} type="submit">
            {isCreating ? "Creating..." : "Create interview"}
          </Button>
        </form>

        <div className="grid gap-4">
          <div className="rounded-md border border-slate-800 bg-slate-900/60 p-5">
            <h2 className="text-lg font-semibold">Generated interviews</h2>
            <p className="mt-1 text-sm text-slate-400">
              Open an interview to review the scenario, generated files, invite link, and delete controls.
            </p>
          </div>
          {isLoading ? (
            <div className="rounded-md border border-slate-800 bg-slate-900/60 p-6 text-slate-300">Loading interviews...</div>
          ) : null}
          {!isLoading && sortedInterviews.length === 0 ? (
            <div className="rounded-md border border-slate-800 bg-slate-900/60 p-6 text-slate-300">No interviews yet.</div>
          ) : null}
          {sortedInterviews.map((interview) => (
            <article className="rounded-md border border-slate-800 bg-slate-900/60 p-5" key={interview.id}>
              <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-xl font-semibold">{interview.role_title}</h2>
                    <span className="rounded-full border border-slate-700 px-3 py-1 text-xs font-medium text-slate-300">
                      {interview.status}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-slate-400">
                    {interview.seniority} / {interview.difficulty} / {interview.duration_minutes} minutes
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {interview.stack.map((item) => (
                      <span className="rounded-full bg-slate-950 px-3 py-1 text-xs text-slate-300" key={item}>
                        {item}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Link
                    className="inline-flex h-10 items-center justify-center rounded-md border border-slate-700 px-4 text-sm font-medium text-slate-200 hover:border-cyan-500 hover:text-cyan-200"
                    href={`/interviews/${interview.id}`}
                  >
                    View details
                  </Link>
                  <Button
                    disabled={generatingId === interview.id}
                    onClick={() => void handleGenerateScenario(interview.id)}
                    type="button"
                  >
                    {generatingId === interview.id ? "Generating..." : interview.scenario ? "Regenerate scenario" : "Generate scenario"}
                  </Button>
                  <Button
                    disabled={deletingId === interview.id}
                    onClick={() => void handleDeleteInterview(interview)}
                    type="button"
                    variant="secondary"
                  >
                    {deletingId === interview.id ? "Deleting..." : "Delete"}
                  </Button>
                </div>
              </div>

              <div className="mt-5 grid gap-3 border-t border-slate-800 pt-5">
                <label className="grid gap-2 text-sm text-slate-200" htmlFor={`invite-${interview.id}`}>
                  <span>Candidate invite email</span>
                  <input
                    className="h-11 rounded-md border border-slate-700 bg-slate-950 px-3 text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/20"
                    id={`invite-${interview.id}`}
                    onChange={(event) => updateInviteEmail(interview.id, event.target.value)}
                    placeholder="candidate@nexterview.dev"
                    type="email"
                    value={inviteEmails[interview.id] ?? DEFAULT_INVITE_EMAIL}
                  />
                </label>
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                  <Button
                    disabled={inviteGeneratingId === interview.id || !interview.scenario}
                    onClick={() => void handleCreateInvite(interview.id)}
                    type="button"
                    variant="secondary"
                  >
                    {inviteGeneratingId === interview.id ? "Generating invite..." : "Generate invite link"}
                  </Button>
                  {inviteLinks[interview.id] ? (
                    <a
                      className="break-all text-sm font-medium text-cyan-300 hover:text-cyan-200"
                      href={inviteLinks[interview.id]}
                    >
                      {inviteLinks[interview.id]}
                    </a>
                  ) : null}
                </div>
                {!interview.scenario ? (
                  <p className="text-xs text-slate-500">Generate the scenario first, then create the candidate invite link.</p>
                ) : null}
              </div>

              {interview.scenario ? (
                <div className="mt-5 grid gap-4 border-t border-slate-800 pt-5">
                  <div>
                    <p className="text-sm text-cyan-200">{interview.scenario.generation_source}</p>
                    <h3 className="mt-1 text-lg font-semibold">{interview.scenario.title}</h3>
                    <p className="mt-2 text-sm leading-6 text-slate-300">{interview.scenario.business_context}</p>
                  </div>
                  <div className="grid gap-4 xl:grid-cols-2">
                    <section>
                      <h4 className="text-sm font-semibold text-slate-200">Technical requirements</h4>
                      <ul className="mt-2 grid gap-2 text-sm text-slate-400">
                        {interview.scenario.technical_requirements.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </section>
                    <section>
                      <h4 className="text-sm font-semibold text-slate-200">Hidden evaluation points</h4>
                      <ul className="mt-2 grid gap-2 text-sm text-slate-400">
                        {interview.scenario.hidden_evaluation_points.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </section>
                  </div>
                  <pre className="max-h-72 overflow-auto rounded-md border border-slate-800 bg-slate-950 p-4 text-xs leading-5 text-slate-300">
                    {interview.scenario.starter_code}
                  </pre>
                  {interview.scenario.project ? <ProjectFilesPreview project={interview.scenario.project} /> : null}
                </div>
              ) : null}
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}

export default function InterviewsPage() {
  return (
    <ProtectedRoute>
      <InterviewsContent />
    </ProtectedRoute>
  );
}
