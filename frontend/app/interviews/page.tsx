"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/app/app-shell";
import {
  EmptyState,
  ErrorState,
  FormSection,
  LoadingState,
  PageHeader,
  StatusBadge,
  formatDate,
  statusTone,
} from "@/components/app/page-primitives";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { useAuth } from "@/components/auth/auth-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError, createInterview, deleteInterview, generateScenario, getInterviews, getResultsDashboard } from "@/lib/api";
import type { Interview, InterviewCreateInput, ResultsDashboardItem } from "@/lib/types";

const DEFAULT_CRITERIA = [
  "Correctness and edge-case handling",
  "Debugging process and verification discipline",
  "Code quality, maintainability, and error handling",
  "AI collaboration quality and ability to validate suggestions",
].join("\n");

const STACK_OPTIONS = [
  "Python + FastAPI",
  "Node.js + Express",
  "React + Next.js",
  "PostgreSQL",
  "Redis",
  "Docker",
  "AWS",
  "Generic full-stack",
];

const SENIORITY_OPTIONS = ["Junior", "Mid-level", "Senior", "Staff"];
const DIFFICULTY_OPTIONS = ["Foundational", "Intermediate", "Advanced"];
const INTERVIEW_TYPE_OPTIONS = [
  "Full-stack feature implementation",
  "Backend debugging",
  "API design",
  "Frontend bug fix",
  "System design written task",
  "AI engineering task",
  "Refactoring task",
  "Security review task",
];
const AI_MODE_OPTIONS = ["Hint Mode", "Pair Programmer Mode", "Senior Engineer Mode", "Debugging Assistant Mode"];

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
  role_title: "",
  seniority: "Senior",
  stack: "Python + FastAPI, PostgreSQL, Redis, Docker",
  difficulty: "Intermediate",
  interview_type: "Backend debugging",
  duration_minutes: "75",
  allowed_ai_mode: "Pair Programmer Mode",
  evaluation_criteria: DEFAULT_CRITERIA,
};

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
    role_title: form.role_title.trim(),
    seniority: form.seniority,
    stack: splitCommaList(form.stack),
    difficulty: form.difficulty,
    interview_type: form.interview_type,
    duration_minutes: Number(form.duration_minutes),
    allowed_ai_mode: form.allowed_ai_mode,
    evaluation_criteria: splitLineList(form.evaluation_criteria),
  };
}

function SelectField({
  id,
  label,
  value,
  options,
  onChange,
  description,
}: {
  id: string;
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
  description?: string;
}) {
  return (
    <label className="grid gap-2 text-sm text-slate-200" htmlFor={id}>
      <span>{label}</span>
      <select
        className="h-11 rounded-md border border-slate-700 bg-slate-950 px-3 text-slate-100 outline-none transition focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/20"
        id={id}
        onChange={(event) => onChange(event.target.value)}
        value={value}
      >
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
      {description ? <span className="text-xs leading-5 text-slate-500">{description}</span> : null}
    </label>
  );
}

function InterviewsContent() {
  const { token, user } = useAuth();
  const [form, setForm] = useState<InterviewFormState>(DEFAULT_FORM);
  const [interviews, setInterviews] = useState<Interview[]>([]);
  const [sessions, setSessions] = useState<ResultsDashboardItem[]>([]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [generatingId, setGeneratingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const canManageInterviews = user?.role === "ADMIN" || user?.role === "INTERVIEWER";

  useEffect(() => {
    if (!token || !canManageInterviews) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    Promise.all([getInterviews(token), getResultsDashboard(token)])
      .then(([loadedInterviews, loadedSessions]) => {
        setInterviews(loadedInterviews);
        setSessions(loadedSessions);
      })
      .catch((requestError: unknown) => {
        const message = requestError instanceof ApiError ? requestError.message : "Unable to load interviews.";
        setError(message);
      })
      .finally(() => setIsLoading(false));
  }, [canManageInterviews, token]);

  const sessionCounts = useMemo(() => {
    const counts = new Map<string, number>();
    sessions.forEach((session) => counts.set(session.interview_id, (counts.get(session.interview_id) ?? 0) + 1));
    return counts;
  }, [sessions]);

  const statusOptions = useMemo(
    () => ["all", ...Array.from(new Set(interviews.map((interview) => interview.status))).sort()],
    [interviews],
  );

  const filteredInterviews = useMemo(() => {
    const query = search.trim().toLowerCase();
    return [...interviews]
      .sort((first, second) => Date.parse(second.created_at) - Date.parse(first.created_at))
      .filter((interview) => statusFilter === "all" || interview.status === statusFilter)
      .filter((interview) => {
        if (!query) {
          return true;
        }
        const searchable = [
          interview.role_title,
          interview.seniority,
          interview.difficulty,
          interview.interview_type,
          interview.status,
          interview.scenario?.title ?? "",
          interview.stack.join(" "),
        ]
          .join(" ")
          .toLowerCase();
        return searchable.includes(query);
      });
  }, [interviews, search, statusFilter]);

  function updateField(field: keyof InterviewFormState, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function validateForm(input: InterviewCreateInput): string | null {
    if (!input.role_title) {
      return "Enter a role title before creating an interview.";
    }
    if (input.stack.length === 0) {
      return "Add at least one stack item.";
    }
    if (!Number.isFinite(input.duration_minutes) || input.duration_minutes < 30 || input.duration_minutes > 240) {
      return "Duration must be between 30 and 240 minutes.";
    }
    if (input.evaluation_criteria.length === 0) {
      return "Add at least one evaluation criterion.";
    }
    return null;
  }

  async function handleCreateInterview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) {
      return;
    }

    const input = toCreateInput(form);
    const validationMessage = validateForm(input);
    if (validationMessage) {
      setError(validationMessage);
      return;
    }

    setError(null);
    setSuccessMessage(null);
    setIsCreating(true);
    try {
      const created = await createInterview(token, input);
      setInterviews((current) => [created, ...current]);
      setSuccessMessage("Interview created. Generate a scenario when you are ready to invite candidates.");
      setForm((current) => ({ ...current, role_title: "" }));
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
    setSuccessMessage(null);
    setGeneratingId(interviewId);
    try {
      const scenario = await generateScenario(token, interviewId);
      setInterviews((current) =>
        current.map((interview) =>
          interview.id === interviewId ? { ...interview, scenario, status: "READY" } : interview,
        ),
      );
      setSuccessMessage("Scenario generated. Open the interview to review it and create an invite.");
    } catch (requestError: unknown) {
      const message = requestError instanceof ApiError ? requestError.message : "Unable to generate scenario.";
      setError(message);
    } finally {
      setGeneratingId(null);
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
    setSuccessMessage(null);
    setDeletingId(interview.id);
    try {
      await deleteInterview(token, interview.id);
      setInterviews((current) => current.filter((item) => item.id !== interview.id));
      setSuccessMessage("Interview deleted.");
    } catch (requestError: unknown) {
      const message = requestError instanceof ApiError ? requestError.message : "Unable to delete interview.";
      setError(message);
    } finally {
      setDeletingId(null);
    }
  }

  if (!canManageInterviews) {
    return (
      <AppShell>
        <PageHeader
          description="Interview management is available to admin and interviewer roles."
          eyebrow="Access"
          title="Interviews"
        />
        <div className="mt-6">
          <EmptyState description="Your current role cannot manage interviews." title="Interview management unavailable" />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <PageHeader
        description="Create realistic role-based interviews, generate scenarios, and manage candidate sessions."
        eyebrow="Interview operations"
        title="Interviews"
      />

      <section className="mt-6 grid gap-5 xl:grid-cols-[390px_minmax(0,1fr)]">
        <form
          className="grid gap-4 rounded-md border border-slate-800 bg-slate-900/70 p-4"
          id="create-interview"
          onSubmit={handleCreateInterview}
        >
          <div>
            <h2 className="text-lg font-semibold text-slate-100">Create interview</h2>
            <p className="mt-1 text-sm leading-6 text-slate-400">
              Configure the hiring signal. Scenario generation happens after creation so reviewers can inspect it first.
            </p>
          </div>

          <FormSection title="Role Details" description="Define who this interview is designed to evaluate.">
            <Input
              id="role_title"
              label="Role title"
              onChange={(event) => updateField("role_title", event.target.value)}
              placeholder="Backend Platform Engineer"
              required
              value={form.role_title}
            />
            <SelectField
              id="seniority"
              label="Seniority"
              onChange={(value) => updateField("seniority", value)}
              options={SENIORITY_OPTIONS}
              value={form.seniority}
            />
          </FormSection>

          <FormSection title="Stack & Interview Type" description="Choose the technologies and shape of work the candidate will see.">
            <label className="grid gap-2 text-sm text-slate-200" htmlFor="stack">
              <span>Stack</span>
              <textarea
                className="min-h-24 rounded-md border border-slate-700 bg-slate-950 px-3 py-3 text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/20"
                id="stack"
                onChange={(event) => updateField("stack", event.target.value)}
                placeholder={STACK_OPTIONS.join(", ")}
                required
                value={form.stack}
              />
              <span className="text-xs leading-5 text-slate-500">Comma-separated. Keep this close to the actual role.</span>
            </label>
            <div className="grid gap-4 sm:grid-cols-2">
              <SelectField
                id="interview_type"
                label="Interview type"
                onChange={(value) => updateField("interview_type", value)}
                options={INTERVIEW_TYPE_OPTIONS}
                value={form.interview_type}
              />
              <SelectField
                id="difficulty"
                label="Difficulty"
                onChange={(value) => updateField("difficulty", value)}
                options={DIFFICULTY_OPTIONS}
                value={form.difficulty}
              />
            </div>
          </FormSection>

          <FormSection title="AI Assistance Settings" description="Candidates may use the AI copilot; their judgment and validation are evaluated.">
            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                id="duration_minutes"
                label="Duration minutes"
                max={240}
                min={30}
                onChange={(event) => updateField("duration_minutes", event.target.value)}
                required
                type="number"
                value={form.duration_minutes}
              />
              <SelectField
                id="allowed_ai_mode"
                label="Allowed AI mode"
                onChange={(value) => updateField("allowed_ai_mode", value)}
                options={AI_MODE_OPTIONS}
                value={form.allowed_ai_mode}
              />
            </div>
          </FormSection>

          <FormSection title="Evaluation Settings" description="Use candidate-visible and reviewer-visible criteria, without prompt internals.">
            <label className="grid gap-2 text-sm text-slate-200" htmlFor="evaluation_criteria">
              <span>Evaluation criteria</span>
              <textarea
                className="min-h-36 rounded-md border border-slate-700 bg-slate-950 px-3 py-3 text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/20"
                id="evaluation_criteria"
                onChange={(event) => updateField("evaluation_criteria", event.target.value)}
                required
                value={form.evaluation_criteria}
              />
              <span className="text-xs leading-5 text-slate-500">One criterion per line.</span>
            </label>
          </FormSection>

          {error ? <ErrorState message={error} /> : null}
          {successMessage ? (
            <p className="rounded-md border border-emerald-900/70 bg-emerald-950/40 px-3 py-2 text-sm text-emerald-200">
              {successMessage}
            </p>
          ) : null}
          <Button aria-busy={isCreating} disabled={isCreating} type="submit">
            {isCreating ? "Creating..." : "Create interview"}
          </Button>
        </form>

        <div className="grid min-w-0 gap-3">
          <section className="rounded-md border border-slate-800 bg-slate-900/70 px-3 py-3">
            <div className="grid gap-3 lg:grid-cols-[auto_minmax(260px,1fr)_180px] lg:items-center">
              <div className="min-w-0">
                <h2 className="text-base font-semibold text-slate-100">Interview list</h2>
                <p className="text-xs text-slate-500">{filteredInterviews.length} shown</p>
              </div>
              <div>
                <label className="grid gap-2 text-sm text-slate-200" htmlFor="interview-search">
                  <span className="sr-only">Search interviews</span>
                  <input
                    className="h-10 rounded-md border border-slate-700 bg-slate-950 px-3 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/20"
                    id="interview-search"
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Search role, stack, type"
                    value={search}
                  />
                </label>
              </div>
              <div>
                <label className="grid gap-2 text-sm text-slate-200" htmlFor="status-filter">
                  <span className="sr-only">Filter by status</span>
                  <select
                    className="h-10 rounded-md border border-slate-700 bg-slate-950 px-3 text-sm text-slate-100 outline-none transition focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/20"
                    id="status-filter"
                    onChange={(event) => setStatusFilter(event.target.value)}
                    value={statusFilter}
                  >
                    {statusOptions.map((status) => (
                      <option key={status} value={status}>
                        {status === "all" ? "All statuses" : status}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            </div>
          </section>

          {isLoading ? <LoadingState label="Loading interviews" rows={4} /> : null}

          {!isLoading && interviews.length === 0 ? (
            <EmptyState
              actionHref="#create-interview"
              actionLabel="Create interview"
              description="Create an interview, generate a scenario, then send an invite from the detail page."
              title="No interviews yet"
            />
          ) : null}

          {!isLoading && interviews.length > 0 && filteredInterviews.length === 0 ? (
            <EmptyState description="Try a different search term or status filter." title="No interviews match your filters" />
          ) : null}

          {filteredInterviews.length ? (
            <section className="overflow-hidden rounded-md border border-slate-800 bg-slate-900/70">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-800 text-left text-sm">
                  <thead className="bg-slate-950/60 text-xs uppercase tracking-wide text-slate-500">
                    <tr>
                      <th className="px-4 py-3 font-medium">Title</th>
                      <th className="px-4 py-3 font-medium">Stack</th>
                      <th className="px-4 py-3 font-medium">Difficulty</th>
                      <th className="px-4 py-3 font-medium">Status</th>
                      <th className="px-4 py-3 font-medium">Candidates</th>
                      <th className="px-4 py-3 font-medium">Created</th>
                      <th className="px-4 py-3 font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {filteredInterviews.map((interview) => (
                      <tr className="hover:bg-slate-950/60" key={interview.id}>
                        <td className="max-w-xs px-4 py-4">
                          <p className="font-medium text-slate-100">{interview.scenario?.title ?? interview.role_title}</p>
                          <p className="mt-1 text-xs text-slate-500">
                            {interview.role_title} / {interview.interview_type} / {interview.duration_minutes} min
                          </p>
                        </td>
                        <td className="px-4 py-4">
                          <div className="flex max-w-sm flex-wrap gap-1.5">
                            {interview.stack.slice(0, 4).map((item) => (
                              <span className="rounded-md border border-slate-800 bg-slate-950 px-2 py-1 text-xs text-slate-300" key={item}>
                                {item}
                              </span>
                            ))}
                            {interview.stack.length > 4 ? <span className="text-xs text-slate-500">+{interview.stack.length - 4}</span> : null}
                          </div>
                        </td>
                        <td className="px-4 py-4 text-slate-300">
                          {interview.seniority} / {interview.difficulty}
                        </td>
                        <td className="px-4 py-4">
                          <StatusBadge label={interview.status} tone={statusTone(interview.status)} />
                        </td>
                        <td className="px-4 py-4 text-slate-300">{sessionCounts.get(interview.id) ?? 0}</td>
                        <td className="px-4 py-4 text-slate-400">{formatDate(interview.created_at)}</td>
                        <td className="px-4 py-4">
                          <div className="flex flex-wrap gap-2">
                            <Link
                              className="inline-flex h-9 items-center justify-center rounded-md border border-slate-700 px-3 text-xs font-medium text-slate-200 hover:border-cyan-500 hover:text-cyan-200"
                              href={`/interviews/${interview.id}`}
                            >
                              Details
                            </Link>
                            <Button
                              className="h-9 px-3 text-xs"
                              aria-busy={generatingId === interview.id}
                              disabled={generatingId === interview.id}
                              onClick={() => void handleGenerateScenario(interview.id)}
                              type="button"
                            >
                              {generatingId === interview.id ? "Generating..." : interview.scenario ? "Regenerate" : "Generate"}
                            </Button>
                            <Button
                              className="h-9 px-3 text-xs"
                              aria-busy={deletingId === interview.id}
                              disabled={deletingId === interview.id}
                              onClick={() => void handleDeleteInterview(interview)}
                              type="button"
                              variant="secondary"
                            >
                              {deletingId === interview.id ? "Deleting..." : "Delete"}
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          ) : null}
        </div>
      </section>
    </AppShell>
  );
}

export default function InterviewsPage() {
  return (
    <ProtectedRoute>
      <InterviewsContent />
    </ProtectedRoute>
  );
}
