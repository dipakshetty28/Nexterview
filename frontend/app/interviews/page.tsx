"use client";

import Link from "next/link";
import { FormEvent, type ReactNode, useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/app/app-shell";
import {
  EmptyState,
  ErrorState,
  FormSection,
  InfoTooltip,
  LoadingState,
  PageHeader,
  SectionHeader,
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
}: {
  id: string;
  label: ReactNode;
  value: string;
  options: string[];
  onChange: (value: string) => void;
}) {
  return (
    <label className="grid gap-2 text-sm text-slate-700" htmlFor={id}>
      <span className="inline-flex items-center gap-2 font-medium">{label}</span>
      <select
        className="h-11 rounded-lg border border-slate-300 bg-white px-3 text-slate-950 shadow-sm outline-none transition hover:border-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
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
    </label>
  );
}

function FilterSelect({
  id,
  label,
  value,
  options,
  onChange,
}: {
  id: string;
  label: string;
  value: string;
  options: Array<{ label: string; value: string }>;
  onChange: (value: string) => void;
}) {
  return (
    <label className="min-w-36" htmlFor={id}>
      <span className="sr-only">{label}</span>
      <select
        className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-700 shadow-sm outline-none transition hover:border-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
        id={id}
        onChange={(event) => onChange(event.target.value)}
        value={value}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
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
  const [stackFilter, setStackFilter] = useState("all");
  const [difficultyFilter, setDifficultyFilter] = useState("all");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [generatingId, setGeneratingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const canManageInterviews = user?.role === "ADMIN" || user?.role === "INTERVIEWER";

  useEffect(() => {
    if (window.location.hash === "#create-interview") {
      setIsCreateOpen(true);
    }
  }, []);

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

  const readyReviewCounts = useMemo(() => {
    const counts = new Map<string, number>();
    sessions
      .filter((session) => ["submitted", "ready_for_review"].includes(session.status) && session.weighted_score === null)
      .forEach((session) => counts.set(session.interview_id, (counts.get(session.interview_id) ?? 0) + 1));
    return counts;
  }, [sessions]);

  const statusOptions = useMemo(
    () => ["all", ...Array.from(new Set(interviews.map((interview) => interview.status))).sort()],
    [interviews],
  );
  const stackOptions = useMemo(
    () => ["all", ...Array.from(new Set(interviews.flatMap((interview) => interview.stack))).sort()],
    [interviews],
  );
  const difficultyOptions = useMemo(
    () => ["all", ...Array.from(new Set(interviews.map((interview) => interview.difficulty))).sort()],
    [interviews],
  );

  const filteredInterviews = useMemo(() => {
    const query = search.trim().toLowerCase();
    return [...interviews]
      .sort((first, second) => Date.parse(second.created_at) - Date.parse(first.created_at))
      .filter((interview) => statusFilter === "all" || interview.status === statusFilter)
      .filter((interview) => stackFilter === "all" || interview.stack.includes(stackFilter))
      .filter((interview) => difficultyFilter === "all" || interview.difficulty === difficultyFilter)
      .filter((interview) => {
        if (!query) {
          return true;
        }
        return [
          interview.role_title,
          interview.seniority,
          interview.difficulty,
          interview.interview_type,
          interview.status,
          interview.scenario?.title ?? "",
          interview.stack.join(" "),
        ]
          .join(" ")
          .toLowerCase()
          .includes(query);
      });
  }, [difficultyFilter, interviews, search, stackFilter, statusFilter]);

  const hasFilters = Boolean(search || statusFilter !== "all" || stackFilter !== "all" || difficultyFilter !== "all");

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
      setSuccessMessage("Interview created. Open it to generate and approve the candidate scenario.");
      setForm((current) => ({ ...current, role_title: "" }));
      setIsCreateOpen(false);
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
          interview.id === interviewId ? { ...interview, scenario, status: "SCENARIO_GENERATED" } : interview,
        ),
      );
      setSuccessMessage("Scenario generated. Open the interview to review and approve it.");
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

  function clearFilters() {
    setSearch("");
    setStatusFilter("all");
    setStackFilter("all");
    setDifficultyFilter("all");
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
        description="Manage scenario readiness, candidate activity, and review work from one operational view."
        eyebrow="Interview operations"
        title="Interviews"
      />

      <div className="mt-5 grid gap-4">
        {error ? <ErrorState message={error} /> : null}
        {successMessage ? (
          <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700" role="status">
            {successMessage}
          </p>
        ) : null}

        <section className="rounded-card border border-white/80 bg-white p-3 shadow-panel">
          <div className="flex flex-col gap-3 xl:flex-row xl:items-center">
            <div className="relative min-w-64 flex-1">
              <label className="sr-only" htmlFor="interview-search">
                Search interviews
              </label>
              <input
                className="h-10 w-full rounded-lg border border-slate-300 bg-slate-50 px-3 text-sm text-slate-950 outline-none transition placeholder:text-slate-400 hover:border-slate-400 focus:border-blue-500 focus:bg-white focus:ring-2 focus:ring-blue-500/20"
                id="interview-search"
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search role, scenario, stack, or interview type"
                value={search}
              />
            </div>
            <div className="flex flex-1 flex-wrap gap-2 xl:justify-end">
              <FilterSelect
                id="status-filter"
                label="Filter by status"
                onChange={setStatusFilter}
                options={statusOptions.map((status) => ({
                  label: status === "all" ? "All statuses" : status.replace(/_/g, " "),
                  value: status,
                }))}
                value={statusFilter}
              />
              <FilterSelect
                id="stack-filter"
                label="Filter by stack"
                onChange={setStackFilter}
                options={stackOptions.map((stack) => ({ label: stack === "all" ? "All stacks" : stack, value: stack }))}
                value={stackFilter}
              />
              <FilterSelect
                id="difficulty-filter"
                label="Filter by difficulty"
                onChange={setDifficultyFilter}
                options={difficultyOptions.map((difficulty) => ({
                  label: difficulty === "all" ? "All difficulties" : difficulty,
                  value: difficulty,
                }))}
                value={difficultyFilter}
              />
              {hasFilters ? (
                <Button className="h-10 px-3" onClick={clearFilters} type="button" variant="ghost">
                  Clear
                </Button>
              ) : null}
              <Button
                className="h-10"
                onClick={() => setIsCreateOpen((current) => !current)}
                type="button"
                variant={isCreateOpen ? "secondary" : "primary"}
              >
                {isCreateOpen ? "Close form" : "Create interview"}
              </Button>
            </div>
          </div>
        </section>

        {isCreateOpen ? (
          <form
            className="grid gap-5 rounded-card border border-blue-100 bg-white p-5 shadow-elevated"
            id="create-interview"
            onSubmit={handleCreateInterview}
          >
            <SectionHeader
              description="Configure the role and evaluation signal. Scenario generation remains a separate approval step."
              title="Create interview"
            />
            <div className="grid gap-4 xl:grid-cols-3">
              <FormSection title="Role" description="Define the candidate profile.">
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
                <SelectField
                  id="difficulty"
                  label="Difficulty"
                  onChange={(value) => updateField("difficulty", value)}
                  options={DIFFICULTY_OPTIONS}
                  value={form.difficulty}
                />
              </FormSection>

              <FormSection title="Scenario shape" description="Match the work to the real role.">
                <label className="grid gap-2 text-sm text-slate-700" htmlFor="stack">
                  <span className="font-medium">Stack</span>
                  <textarea
                    className="min-h-24 rounded-lg border border-slate-300 bg-white px-3 py-3 text-slate-950 shadow-sm outline-none transition placeholder:text-slate-400 hover:border-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
                    id="stack"
                    onChange={(event) => updateField("stack", event.target.value)}
                    placeholder={STACK_OPTIONS.join(", ")}
                    required
                    value={form.stack}
                  />
                </label>
                <SelectField
                  id="interview_type"
                  label="Interview type"
                  onChange={(value) => updateField("interview_type", value)}
                  options={INTERVIEW_TYPE_OPTIONS}
                  value={form.interview_type}
                />
              </FormSection>

              <FormSection title="Session settings" description="Set time and AI assistance.">
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
                  label={
                    <>
                      Allowed AI mode
                      <InfoTooltip
                        content="Sets the assistant behavior available to candidates. Their validation and judgment are still evaluated."
                        label="Allowed AI mode help"
                      />
                    </>
                  }
                  onChange={(value) => updateField("allowed_ai_mode", value)}
                  options={AI_MODE_OPTIONS}
                  value={form.allowed_ai_mode}
                />
              </FormSection>
            </div>

            <FormSection title="Evaluation criteria" description="One criterion per line. These guide scenario and review quality.">
              <textarea
                className="min-h-28 rounded-lg border border-slate-300 bg-white px-3 py-3 text-slate-950 shadow-sm outline-none transition hover:border-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
                id="evaluation_criteria"
                onChange={(event) => updateField("evaluation_criteria", event.target.value)}
                required
                value={form.evaluation_criteria}
              />
            </FormSection>

            <div className="flex justify-end gap-2">
              <Button onClick={() => setIsCreateOpen(false)} type="button" variant="ghost">
                Cancel
              </Button>
              <Button aria-busy={isCreating} disabled={isCreating} type="submit">
                {isCreating ? "Creating..." : "Create interview"}
              </Button>
            </div>
          </form>
        ) : null}

        {isLoading ? <LoadingState label="Loading interviews" rows={4} /> : null}

        {!isLoading && interviews.length === 0 ? (
          <EmptyState
            action={
              <Button onClick={() => setIsCreateOpen(true)} type="button">
                Create interview
              </Button>
            }
            description="Configure a role, generate a realistic scenario, and invite the first candidate."
            title="No interviews yet"
          />
        ) : null}

        {!isLoading && interviews.length > 0 ? (
          <section className="overflow-hidden rounded-card border border-white/80 bg-white shadow-panel">
            <div className="border-b border-slate-200 px-5 py-4">
              <SectionHeader
                aside={<span className="text-xs font-semibold uppercase tracking-wide text-slate-500">{filteredInterviews.length} shown</span>}
                description="Scenario readiness, candidate volume, and outstanding review work."
                title="Interview pipeline"
              />
            </div>

            {filteredInterviews.length === 0 ? (
              <div className="p-5">
                <EmptyState
                  action={
                    <Button onClick={clearFilters} type="button" variant="secondary">
                      Clear filters
                    </Button>
                  }
                  description="Try a different search term or reset the active filters."
                  embedded
                  title="No interviews match"
                />
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="table-surface">
                  <thead className="table-head">
                    <tr>
                      <th className="px-5 py-3 font-medium">Interview</th>
                      <th className="px-5 py-3 font-medium">Stack</th>
                      <th className="px-5 py-3 font-medium">Status</th>
                      <th className="px-5 py-3 font-medium">Candidates</th>
                      <th className="px-5 py-3 font-medium">Review status</th>
                      <th className="px-5 py-3 font-medium">Created</th>
                      <th className="px-5 py-3 text-right font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {filteredInterviews.map((interview) => {
                      const candidateCount = sessionCounts.get(interview.id) ?? 0;
                      const readyCount = readyReviewCounts.get(interview.id) ?? 0;
                      return (
                        <tr className="table-row" key={interview.id}>
                          <td className="max-w-sm px-5 py-3.5">
                            <Link className="font-semibold text-slate-950 hover:text-blue-700" href={`/interviews/${interview.id}`}>
                              {interview.role_title}
                            </Link>
                            <p className="mt-1 truncate text-xs text-slate-500">
                              {interview.scenario?.title ?? interview.interview_type} / {interview.seniority} / {interview.difficulty}
                            </p>
                          </td>
                          <td className="px-5 py-3.5">
                            <div className="flex max-w-xs flex-wrap gap-1.5">
                              {interview.stack.slice(0, 2).map((item) => (
                                <span
                                  className="rounded-full border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-medium text-slate-600"
                                  key={item}
                                >
                                  {item}
                                </span>
                              ))}
                              {interview.stack.length > 2 ? (
                                <span className="px-1 py-1 text-xs text-slate-500">+{interview.stack.length - 2}</span>
                              ) : null}
                            </div>
                          </td>
                          <td className="px-5 py-3.5">
                            <StatusBadge label={interview.status} tone={statusTone(interview.status)} />
                          </td>
                          <td className="px-5 py-3.5">
                            <span className="font-semibold text-slate-900">{candidateCount}</span>
                            <span className="ml-1 text-xs text-slate-500">sessions</span>
                          </td>
                          <td className="px-5 py-3.5">
                            <StatusBadge
                              label={readyCount ? `${readyCount} ready` : candidateCount ? "Up to date" : "No sessions"}
                              tone={readyCount ? "warning" : candidateCount ? "success" : "neutral"}
                            />
                          </td>
                          <td className="whitespace-nowrap px-5 py-3.5 text-slate-600">{formatDate(interview.created_at)}</td>
                          <td className="px-5 py-3.5">
                            <div className="flex justify-end">
                              <details className="relative">
                                <summary className="flex h-9 cursor-pointer list-none items-center rounded-lg border border-slate-300 bg-white px-3 text-xs font-semibold text-slate-700 shadow-sm transition hover:border-slate-400 hover:bg-slate-50">
                                  Actions
                                </summary>
                                <div className="absolute right-0 z-20 mt-2 grid w-48 gap-1 rounded-lg border border-slate-200 bg-white p-2 shadow-elevated">
                                  <Link
                                    className="rounded-md px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 hover:text-slate-950"
                                    href={`/interviews/${interview.id}`}
                                  >
                                    Open control center
                                  </Link>
                                  <button
                                    className="rounded-md px-3 py-2 text-left text-sm font-medium text-slate-700 hover:bg-slate-100 hover:text-slate-950 disabled:opacity-50"
                                    disabled={generatingId === interview.id}
                                    onClick={() => void handleGenerateScenario(interview.id)}
                                    type="button"
                                  >
                                    {generatingId === interview.id
                                      ? "Generating..."
                                      : interview.scenario
                                        ? "Regenerate scenario"
                                        : "Generate scenario"}
                                  </button>
                                  <button
                                    className="rounded-md px-3 py-2 text-left text-sm font-medium text-rose-700 hover:bg-rose-50 disabled:opacity-50"
                                    disabled={deletingId === interview.id}
                                    onClick={() => void handleDeleteInterview(interview)}
                                    type="button"
                                  >
                                    {deletingId === interview.id ? "Deleting..." : "Delete interview"}
                                  </button>
                                </div>
                              </details>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        ) : null}
      </div>
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
