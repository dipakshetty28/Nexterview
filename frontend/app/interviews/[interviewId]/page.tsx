"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/app/app-shell";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  StatCard,
  StatusBadge,
  formatDateTime,
  statusTone,
} from "@/components/app/page-primitives";
import { useAuth } from "@/components/auth/auth-provider";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  ApiError,
  createCandidateInvite,
  deleteInterview,
  generateScenario,
  getInterview,
  getInterviewSubmissions,
} from "@/lib/api";
import type { Interview, InterviewSubmissionResult, ProjectFile, ScenarioProject } from "@/lib/types";

const DEFAULT_INVITE_EMAIL = "";

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
          <h3 className="text-base font-semibold text-slate-100">{project.project_name}</h3>
          <p className="mt-1 text-xs text-slate-500">
            {project.framework ?? "Project"} / {project.package_manager ?? "package manager"} / {project.files.length} files
          </p>
        </div>
        <div className="grid gap-1 text-xs text-slate-400 md:text-right">
          <span>Environment: pre-provisioned</span>
          <span>Checks: pass/fail runner configured</span>
          {project.entrypoint ? <span>Entrypoint: {project.entrypoint}</span> : null}
        </div>
      </div>
      <div className="grid gap-2">
        {project.files.map((file) => (
          <details className={`rounded-md border ${fileTone(file)}`} key={file.path}>
            <summary className="cursor-pointer px-3 py-2 text-sm font-medium">
              <span>{file.path}</span>
              <span className="ml-2 text-xs opacity-70">
                {file.language} / {file.file_type}
                {file.is_hidden ? " / reviewer-only" : ""}
              </span>
            </summary>
            <pre className="max-h-96 overflow-auto border-t border-inherit bg-slate-950 p-3 text-xs leading-5 text-slate-200">
              {file.content}
            </pre>
          </details>
        ))}
      </div>
    </section>
  );
}

function ReviewList({ title, items }: { title: string; items: string[] }) {
  return (
    <section>
      <h3 className="text-sm font-semibold text-slate-100">{title}</h3>
      <ul className="mt-2 grid gap-2 text-sm leading-6 text-slate-400">
        {items.length ? (
          items.map((item) => (
            <li className="rounded-md border border-slate-800 bg-slate-950/60 px-3 py-2" key={item}>
              {item}
            </li>
          ))
        ) : (
          <li className="text-slate-500">None recorded.</li>
        )}
      </ul>
    </section>
  );
}

function CandidateSessionRow({ submission }: { submission: InterviewSubmissionResult }) {
  return (
    <tr className="hover:bg-slate-950/60">
      <td className="px-5 py-4">
        <p className="font-medium text-slate-100">{submission.candidate_name}</p>
        <p className="mt-1 text-xs text-slate-500">{submission.candidate_email}</p>
      </td>
      <td className="px-5 py-4">
        <StatusBadge label={submission.status} tone={statusTone(submission.status)} />
      </td>
      <td className="px-5 py-4 text-slate-400">{formatDateTime(submission.submitted_at)}</td>
      <td className="px-5 py-4 text-slate-300">{submission.test_output ? "Test output submitted" : "No test output"}</td>
      <td className="px-5 py-4">
        {submission.submission_id ? (
          <Link className="font-medium text-cyan-300 hover:text-cyan-200" href={`/results/${submission.session_id}`}>
            View result
          </Link>
        ) : (
          <span className="text-slate-600">Pending submission</span>
        )}
      </td>
    </tr>
  );
}

function InterviewDetailContent() {
  const params = useParams<{ interviewId: string }>();
  const router = useRouter();
  const { token, user } = useAuth();
  const [interview, setInterview] = useState<Interview | null>(null);
  const [submissions, setSubmissions] = useState<InterviewSubmissionResult[]>([]);
  const [inviteEmail, setInviteEmail] = useState(DEFAULT_INVITE_EMAIL);
  const [inviteLink, setInviteLink] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isCreatingInvite, setIsCreatingInvite] = useState(false);
  const [isCopied, setIsCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const canManageInterviews = user?.role === "ADMIN" || user?.role === "INTERVIEWER";
  const submittedCount = submissions.filter((submission) => submission.status === "submitted" || submission.status === "reviewed").length;
  const reviewedCount = submissions.filter((submission) => submission.status === "reviewed").length;

  useEffect(() => {
    if (!token || !params.interviewId || !canManageInterviews) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    Promise.all([getInterview(token, params.interviewId), getInterviewSubmissions(token, params.interviewId)])
      .then(([loadedInterview, loadedSubmissions]) => {
        setInterview(loadedInterview);
        setSubmissions(loadedSubmissions);
      })
      .catch((requestError: unknown) => {
        const message = requestError instanceof ApiError ? requestError.message : "Unable to load interview.";
        setError(message);
      })
      .finally(() => setIsLoading(false));
  }, [canManageInterviews, params.interviewId, token]);

  async function handleGenerateScenario() {
    if (!token || !interview) {
      return;
    }
    setIsGenerating(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const scenario = await generateScenario(token, interview.id);
      setInterview({ ...interview, scenario, status: "READY" });
      setSuccessMessage("Scenario generated. Review the task before inviting candidates.");
    } catch (requestError: unknown) {
      const message = requestError instanceof ApiError ? requestError.message : "Unable to generate scenario.";
      setError(message);
    } finally {
      setIsGenerating(false);
    }
  }

  async function handleCreateInvite() {
    if (!token || !interview) {
      return;
    }
    const candidateEmail = inviteEmail.trim();
    if (!candidateEmail) {
      setError("Enter a candidate email before creating an invite.");
      return;
    }

    setIsCreatingInvite(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const invite = await createCandidateInvite(token, interview.id, { candidate_email: candidateEmail });
      setInviteLink(invite.invite_url);
      setSuccessMessage("Invite link created.");
    } catch (requestError: unknown) {
      const message = requestError instanceof ApiError ? requestError.message : "Unable to create invite.";
      setError(message);
    } finally {
      setIsCreatingInvite(false);
    }
  }

  async function handleCopyInvite() {
    if (!inviteLink) {
      return;
    }
    try {
      await navigator.clipboard.writeText(inviteLink);
      setIsCopied(true);
      window.setTimeout(() => setIsCopied(false), 1500);
    } catch {
      setIsCopied(false);
    }
  }

  async function handleDeleteInterview() {
    if (!token || !interview) {
      return;
    }
    const confirmed = window.confirm(`Delete "${interview.role_title}" and all generated scenario/session data?`);
    if (!confirmed) {
      return;
    }

    setIsDeleting(true);
    setError(null);
    setSuccessMessage(null);
    try {
      await deleteInterview(token, interview.id);
      router.push("/interviews");
    } catch (requestError: unknown) {
      const message = requestError instanceof ApiError ? requestError.message : "Unable to delete interview.";
      setError(message);
    } finally {
      setIsDeleting(false);
    }
  }

  if (!canManageInterviews) {
    return (
      <AppShell>
        <PageHeader
          description="Interview details are available to admin and interviewer roles."
          eyebrow="Access"
          title="Interview details"
        />
        <div className="mt-6">
          <EmptyState description="Your current role cannot manage interviews." title="Interview details unavailable" />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <PageHeader
        actions={
          interview ? (
            <>
              <Button disabled={isGenerating} onClick={() => void handleGenerateScenario()} type="button">
                {isGenerating ? "Generating..." : interview.scenario ? "Regenerate scenario" : "Generate scenario"}
              </Button>
              <Button disabled={isDeleting} onClick={() => void handleDeleteInterview()} type="button" variant="secondary">
                {isDeleting ? "Deleting..." : "Delete"}
              </Button>
            </>
          ) : null
        }
        description="Review scenario readiness, invite candidates, and track session outcomes."
        eyebrow="Interview detail"
        title={interview?.role_title ?? "Interview details"}
      />

      <section className="mt-6 grid gap-5">
        {isLoading ? <LoadingState label="Loading interview..." /> : null}
        {error ? <ErrorState message={error} /> : null}
        {successMessage ? (
          <p className="rounded-md border border-emerald-900/70 bg-emerald-950/40 px-3 py-2 text-sm text-emerald-200">
            {successMessage}
          </p>
        ) : null}

        {interview ? (
          <>
            <section className="grid gap-4 lg:grid-cols-4">
              <StatCard description={`${interview.seniority} / ${interview.difficulty}`} label="Role" value={interview.role_title} />
              <StatCard description={interview.interview_type} label="Duration" value={`${interview.duration_minutes} min`} />
              <StatCard description={interview.scenario ? "Scenario ready for review" : "Scenario not generated"} label="Scenario status" tone={statusTone(interview.status)} value={interview.status} />
              <StatCard description={`${submittedCount} submitted, ${reviewedCount} reviewed`} label="Candidate sessions" value={submissions.length} />
            </section>

            <section className="rounded-md border border-slate-800 bg-slate-900/70 p-5">
              <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge label={interview.status} tone={statusTone(interview.status)} />
                    <StatusBadge label={interview.allowed_ai_mode} tone="info" />
                  </div>
                  <h2 className="mt-3 text-lg font-semibold text-slate-100">{interview.role_title}</h2>
                  <p className="mt-2 text-sm leading-6 text-slate-400">
                    Created {formatDateTime(interview.created_at)}. Stack: {interview.stack.join(", ")}
                  </p>
                </div>

                <div className="grid w-full gap-3 xl:w-96">
                  <Input
                    id="candidate_invite_email"
                    label="Candidate invite email"
                    onChange={(event) => setInviteEmail(event.target.value)}
                    placeholder="candidate@example.com"
                    type="email"
                    value={inviteEmail}
                  />
                  <div className="flex flex-col gap-2 sm:flex-row">
                    <Button
                      className="flex-1"
                      disabled={isCreatingInvite || !interview.scenario}
                      onClick={() => void handleCreateInvite()}
                      type="button"
                      variant="secondary"
                    >
                      {isCreatingInvite ? "Creating invite..." : "Create invite"}
                    </Button>
                    <Button
                      className="flex-1"
                      disabled={!inviteLink}
                      onClick={() => void handleCopyInvite()}
                      type="button"
                      variant="ghost"
                    >
                      {isCopied ? "Copied" : "Copy link"}
                    </Button>
                  </div>
                  {inviteLink ? (
                    <p className="break-all rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-cyan-200">
                      {inviteLink}
                    </p>
                  ) : null}
                  {!interview.scenario ? (
                    <p className="text-xs text-slate-500">Generate the scenario before creating an invite.</p>
                  ) : null}
                </div>
              </div>
            </section>

            <section className="rounded-md border border-slate-800 bg-slate-900/70">
              <div className="flex flex-col gap-2 border-b border-slate-800 px-5 py-4 md:flex-row md:items-center md:justify-between">
                <div>
                  <h2 className="text-lg font-semibold">Candidate sessions</h2>
                  <p className="mt-1 text-sm text-slate-400">Candidate activity and result readiness for this interview.</p>
                </div>
                <span className="text-xs uppercase tracking-wide text-slate-500">{submissions.length} sessions</span>
              </div>
              {submissions.length === 0 ? (
                <div className="p-5">
                  <EmptyState
                    description="Create an invite and share it with a candidate. Sessions will appear here after invite use."
                    title="No candidate sessions yet"
                  />
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-slate-800 text-left text-sm">
                    <thead className="bg-slate-950/60 text-xs uppercase tracking-wide text-slate-500">
                      <tr>
                        <th className="px-5 py-3 font-medium">Candidate</th>
                        <th className="px-5 py-3 font-medium">Status</th>
                        <th className="px-5 py-3 font-medium">Submitted</th>
                        <th className="px-5 py-3 font-medium">Validation</th>
                        <th className="px-5 py-3 font-medium">Result</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {submissions.map((submission) => (
                        <CandidateSessionRow key={submission.session_id} submission={submission} />
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            {interview.scenario ? (
              <section className="grid gap-5 rounded-md border border-slate-800 bg-slate-900/70 p-5">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <p className="text-sm font-medium text-cyan-200">Scenario preview</p>
                    <h2 className="mt-1 text-xl font-semibold">{interview.scenario.title}</h2>
                    <p className="mt-2 text-sm leading-6 text-slate-300">{interview.scenario.business_context}</p>
                  </div>
                  <StatusBadge label="Reviewer visible" tone="info" />
                </div>

                <div className="grid gap-4 lg:grid-cols-2">
                  <ReviewList items={interview.scenario.technical_requirements} title="Visible requirements" />
                  <ReviewList items={interview.scenario.expected_behavior} title="Expected behavior" />
                  <ReviewList items={interview.scenario.hidden_evaluation_points} title="Hidden evaluation points" />
                  <ReviewList items={interview.scenario.interviewer_rubric} title="Interviewer rubric" />
                </div>

                <section className="grid gap-3 rounded-md border border-slate-800 bg-slate-950/50 p-4">
                  <h3 className="text-sm font-semibold text-slate-100">Candidate-facing brief</h3>
                  <p className="whitespace-pre-wrap text-sm leading-6 text-slate-300">{interview.scenario.candidate_instructions}</p>
                  <div className="grid gap-3 text-sm leading-6 text-slate-400 md:grid-cols-2">
                    <p>
                      <span className="font-medium text-slate-200">Bug:</span> {interview.scenario.bug_description}
                    </p>
                    <p>
                      <span className="font-medium text-slate-200">Feature:</span> {interview.scenario.feature_request}
                    </p>
                  </div>
                  {interview.scenario.logs_or_bug_report ? (
                    <pre className="max-h-72 overflow-auto whitespace-pre-wrap rounded-md border border-slate-800 bg-slate-950 p-3 text-xs leading-5 text-slate-300">
                      {interview.scenario.logs_or_bug_report}
                    </pre>
                  ) : null}
                </section>

                <section>
                  <h3 className="text-sm font-semibold text-slate-200">Validation instructions</h3>
                  <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-400">
                    {interview.scenario.validation_instructions}
                  </p>
                </section>

                {interview.scenario.project ? <ProjectFilesPreview project={interview.scenario.project} /> : null}
              </section>
            ) : (
              <EmptyState
                description="Generate the scenario to review the task, hidden evaluation points, rubric, and project files."
                title="Scenario not generated"
              />
            )}
          </>
        ) : null}
      </section>
    </AppShell>
  );
}

export default function InterviewDetailPage() {
  return (
    <ProtectedRoute>
      <InterviewDetailContent />
    </ProtectedRoute>
  );
}
