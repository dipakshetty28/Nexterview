"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

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

const DEFAULT_INVITE_EMAIL = "candidate@nexterview.dev";

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
            <pre className="max-h-96 overflow-auto border-t border-inherit bg-slate-950 p-3 text-xs leading-5 text-slate-200">
              {file.content}
            </pre>
          </details>
        ))}
      </div>
    </section>
  );
}

function submissionBranchUrl(submission: InterviewSubmissionResult): string | null {
  if (!submission.repository_url || !submission.branch_name) {
    return null;
  }
  return `${submission.repository_url}/tree/${encodeURIComponent(submission.branch_name)}`;
}

function GitHubSubmissionLinks({ submission }: { submission: InterviewSubmissionResult }) {
  const branchHref = submissionBranchUrl(submission);
  if (!submission.submission_id) {
    return <span className="text-slate-500">No submission yet</span>;
  }
  if (submission.push_status === "pushed") {
    return (
      <div className="grid gap-1">
        {branchHref ? (
          <a className="font-medium text-cyan-300 hover:text-cyan-200" href={branchHref}>
            Branch: {submission.branch_name}
          </a>
        ) : (
          <span>Branch: {submission.branch_name}</span>
        )}
        {submission.pull_request_url ? (
          <a className="font-medium text-cyan-300 hover:text-cyan-200" href={submission.pull_request_url}>
            Pull request
          </a>
        ) : null}
      </div>
    );
  }
  if (submission.push_status === "failed") {
    return <span className="text-amber-300">GitHub push failed; database fallback saved.</span>;
  }
  if (submission.push_status === "no_changes") {
    return <span className="text-slate-400">No changed files to push.</span>;
  }
  return <span className="text-slate-400">GitHub push disabled; database fallback saved.</span>;
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
  const [error, setError] = useState<string | null>(null);

  const canManageInterviews = user?.role === "ADMIN" || user?.role === "INTERVIEWER";

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
    try {
      const scenario = await generateScenario(token, interview.id);
      setInterview({ ...interview, scenario, status: "READY" });
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
    setIsCreatingInvite(true);
    setError(null);
    try {
      const invite = await createCandidateInvite(token, interview.id, { candidate_email: inviteEmail.trim() });
      setInviteLink(invite.invite_url);
    } catch (requestError: unknown) {
      const message = requestError instanceof ApiError ? requestError.message : "Unable to create invite.";
      setError(message);
    } finally {
      setIsCreatingInvite(false);
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
      <main className="min-h-screen bg-slate-950 px-6 py-8 text-slate-100">
        <div className="mx-auto max-w-3xl rounded-md border border-slate-800 bg-slate-900/60 p-6">
          <p className="text-sm text-slate-400">Nexterview</p>
          <h1 className="mt-2 text-2xl font-semibold">Interview details</h1>
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
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-6 py-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <Link className="text-sm font-medium text-cyan-300 hover:text-cyan-200" href="/interviews">
              Back to interviews
            </Link>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight">
              {interview?.role_title ?? "Interview details"}
            </h1>
          </div>
          {interview ? (
            <div className="flex flex-wrap gap-2">
              <Button disabled={isGenerating} onClick={() => void handleGenerateScenario()} type="button">
                {isGenerating ? "Generating..." : interview.scenario ? "Regenerate scenario" : "Generate scenario"}
              </Button>
              <Button disabled={isDeleting} onClick={() => void handleDeleteInterview()} type="button" variant="secondary">
                {isDeleting ? "Deleting..." : "Delete"}
              </Button>
            </div>
          ) : null}
        </div>
      </header>

      <section className="mx-auto grid max-w-6xl gap-5 px-6 py-8">
        {isLoading ? (
          <div className="rounded-md border border-slate-800 bg-slate-900/60 p-6 text-slate-300">Loading interview...</div>
        ) : null}
        {error ? (
          <p className="rounded-md border border-red-900/70 bg-red-950/50 px-3 py-2 text-sm text-red-200">{error}</p>
        ) : null}
        {interview ? (
          <>
            <section className="rounded-md border border-slate-800 bg-slate-900/60 p-5">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
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
                <div className="grid min-w-full gap-3 sm:min-w-80">
                  <Input
                    id="candidate_invite_email"
                    label="Candidate invite email"
                    onChange={(event) => setInviteEmail(event.target.value)}
                    type="email"
                    value={inviteEmail}
                  />
                  <Button
                    disabled={isCreatingInvite || !interview.scenario}
                    onClick={() => void handleCreateInvite()}
                    type="button"
                    variant="secondary"
                  >
                    {isCreatingInvite ? "Generating invite..." : "Generate invite link"}
                  </Button>
                  {inviteLink ? (
                    <a className="break-all text-sm font-medium text-cyan-300 hover:text-cyan-200" href={inviteLink}>
                      {inviteLink}
                    </a>
                  ) : null}
                  {!interview.scenario ? (
                    <p className="text-xs text-slate-500">Generate the scenario first, then create the invite link.</p>
                  ) : null}
                </div>
              </div>
            </section>

            <section className="rounded-md border border-slate-800 bg-slate-900/60 p-5">
              <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                <div>
                  <h2 className="text-lg font-semibold">Candidate submissions</h2>
                  <p className="mt-1 text-sm text-slate-400">Branch and pull request links appear after final submit.</p>
                </div>
                <span className="text-xs uppercase tracking-wide text-slate-500">{submissions.length} sessions</span>
              </div>
              <div className="mt-4 grid gap-3">
                {submissions.length === 0 ? (
                  <p className="rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-400">
                    No candidate sessions yet.
                  </p>
                ) : (
                  submissions.map((submission) => (
                    <div
                      className="grid gap-3 rounded-md border border-slate-800 bg-slate-950 px-3 py-3 text-sm md:grid-cols-[minmax(0,1fr)_auto]"
                      key={submission.session_id}
                    >
                      <div className="min-w-0">
                        <p className="font-medium text-slate-100">{submission.candidate_name}</p>
                        <p className="mt-1 truncate text-xs text-slate-500">{submission.candidate_email}</p>
                        <p className="mt-2 text-xs text-slate-400">
                          {submission.status}
                          {submission.submitted_at ? ` / submitted ${new Date(submission.submitted_at).toLocaleString()}` : ""}
                        </p>
                      </div>
                      <div className="min-w-0 md:min-w-72 md:text-right">
                        <GitHubSubmissionLinks submission={submission} />
                        {submission.submission_id ? (
                          <Link
                            className="mt-2 inline-flex text-xs font-medium text-cyan-300 hover:text-cyan-200"
                            href={`/results/${submission.session_id}`}
                          >
                            View result
                          </Link>
                        ) : null}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </section>

            {interview.scenario ? (
              <section className="grid gap-5 rounded-md border border-slate-800 bg-slate-900/60 p-5">
                <div>
                  <p className="text-sm text-cyan-200">{interview.scenario.generation_source}</p>
                  <h2 className="mt-1 text-xl font-semibold">{interview.scenario.title}</h2>
                  <p className="mt-2 text-sm leading-6 text-slate-300">{interview.scenario.business_context}</p>
                </div>
                <div className="grid gap-4 lg:grid-cols-2">
                  <section>
                    <h3 className="text-sm font-semibold text-slate-200">Technical requirements</h3>
                    <ul className="mt-2 grid gap-2 text-sm text-slate-400">
                      {interview.scenario.technical_requirements.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </section>
                  <section>
                    <h3 className="text-sm font-semibold text-slate-200">Expected behavior</h3>
                    <ul className="mt-2 grid gap-2 text-sm text-slate-400">
                      {interview.scenario.expected_behavior.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </section>
                  <section>
                    <h3 className="text-sm font-semibold text-slate-200">Bug and feature request</h3>
                    <div className="mt-2 grid gap-2 text-sm leading-6 text-slate-400">
                      <p>{interview.scenario.bug_description}</p>
                      <p>{interview.scenario.feature_request}</p>
                    </div>
                  </section>
                  <section>
                    <h3 className="text-sm font-semibold text-slate-200">Hidden rubric</h3>
                    <ul className="mt-2 grid gap-2 text-sm text-slate-400">
                      {interview.scenario.hidden_rubric.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </section>
                </div>
                <section>
                  <h3 className="text-sm font-semibold text-slate-200">Validation instructions</h3>
                  <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-400">
                    {interview.scenario.validation_instructions}
                  </p>
                </section>
                {interview.scenario.project ? <ProjectFilesPreview project={interview.scenario.project} /> : null}
              </section>
            ) : (
              <section className="rounded-md border border-slate-800 bg-slate-900/60 p-5 text-sm text-slate-300">
                This interview does not have a generated scenario yet.
              </section>
            )}
          </>
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
