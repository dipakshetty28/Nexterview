"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/app/app-shell";
import {
  ActionButton,
  EmptyState,
  ErrorState,
  InfoTooltip,
  LoadingState,
  PageHeader,
  SectionHeader,
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
  approveScenario,
  createCandidateInvite,
  deleteInterview,
  generateScenario,
  getInterview,
  getInterviewInvites,
  getInterviewSubmissions,
  regenerateInterviewInvite,
  revokeInterviewInvite,
} from "@/lib/api";
import type {
  Interview,
  InterviewSubmissionResult,
  InviteTokenResponse,
  ProjectFile,
  Scenario,
  ScenarioFilePayload,
  ScenarioProject,
} from "@/lib/types";

const DEFAULT_INVITE_EMAIL = "";
const DEFAULT_INVITE_NAME = "";
const DEFAULT_INVITE_DAYS = 14;
const DEFAULT_INVITE_COUNT = 1;

function fileTone(file: ProjectFile): string {
  if (file.is_hidden) {
    return "border-amber-200 bg-amber-50 text-amber-800";
  }
  if (!file.is_editable) {
    return "border-slate-200 bg-slate-50 text-slate-700";
  }
  return "border-blue-200 bg-blue-50 text-blue-700";
}

function ProjectFilesPreview({ project }: { project: ScenarioProject }) {
  return (
    <section className="grid gap-3 rounded-card border border-slate-200 bg-slate-50/90 p-4">
      <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
        <div>
          <h3 className="text-base font-semibold text-slate-950">{project.project_name}</h3>
          <p className="mt-1 text-xs text-slate-500">
            {project.framework ?? "Project"} / {project.package_manager ?? "package manager"} / {project.files.length} files
          </p>
        </div>
        <div className="flex flex-wrap gap-2 md:justify-end">
          {project.framework ? <StatusBadge label={project.framework} tone="info" /> : null}
          {project.package_manager ? <StatusBadge label={project.package_manager} /> : null}
          {project.entrypoint ? <StatusBadge label={project.entrypoint} /> : null}
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
      <h3 className="text-sm font-semibold text-slate-950">{title}</h3>
      <ul className="mt-2 grid gap-2 text-sm leading-6 text-slate-700">
        {items.length ? (
          items.map((item) => (
            <li className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2" key={item}>
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
    <tr className="table-row">
      <td className="px-5 py-3.5">
        <p className="font-medium text-slate-950">{submission.candidate_name}</p>
        <p className="mt-1 text-xs text-slate-500">{submission.candidate_email}</p>
      </td>
      <td className="px-5 py-3.5">
        <div className="flex flex-wrap gap-2">
          <StatusBadge label={submission.status} tone={statusTone(submission.status)} />
          {submission.invite_status ? (
            <StatusBadge label={submission.invite_status} tone={statusTone(submission.invite_status)} />
          ) : null}
        </div>
      </td>
      <td className="px-5 py-3.5 text-sm text-slate-600">
        <p>Started {formatDateTime(submission.started_at)}</p>
        <p className="mt-1 text-xs">Submitted {formatDateTime(submission.submitted_at)}</p>
      </td>
      <td className="px-5 py-3.5">
        {submission.submission_id ? (
          <Link
            className="inline-flex h-9 items-center rounded-lg border border-slate-300 bg-white px-3 text-xs font-semibold text-slate-700 shadow-sm hover:border-blue-300 hover:text-blue-700"
            href={`/results/${submission.session_id}`}
          >
            View result
          </Link>
        ) : (
          <span className="text-sm text-slate-500">Awaiting submission</span>
        )}
      </td>
    </tr>
  );
}

function ScenarioFilesPreview({ files, title }: { files: ScenarioFilePayload[]; title: string }) {
  return (
    <section className="grid gap-3 rounded-card border border-slate-200 bg-slate-50/90 p-4">
      <div className="flex flex-col gap-1 md:flex-row md:items-center md:justify-between">
        <h3 className="text-sm font-semibold text-slate-950">{title}</h3>
        <span className="text-xs uppercase tracking-wide text-slate-500">{files.length} files</span>
      </div>
      {files.length ? (
        <div className="grid gap-2">
          {files.map((file) => (
            <details className="rounded-md border border-slate-800 bg-slate-950" key={file.path}>
              <summary className="cursor-pointer px-3 py-2 text-sm font-medium text-slate-100">
                <span>{file.path}</span>
                <span className="ml-2 text-xs text-slate-500">{file.language}</span>
              </summary>
              <pre className="max-h-80 overflow-auto border-t border-slate-800 p-3 text-xs leading-5 text-slate-200">
                {file.content}
              </pre>
            </details>
          ))}
        </div>
      ) : (
        <p className="text-sm text-slate-500">No files recorded.</p>
      )}
    </section>
  );
}

function InviteRow({
  invite,
  isCopied,
  isBusy,
  onCopy,
  onRegenerate,
  onRevoke,
}: {
  invite: InviteTokenResponse;
  isCopied: boolean;
  isBusy: boolean;
  onCopy: (invite: InviteTokenResponse) => void;
  onRegenerate: (invite: InviteTokenResponse) => void;
  onRevoke: (invite: InviteTokenResponse) => void;
}) {
  const candidateLabel = invite.candidate_name || invite.candidate_email || "Generic invite";
  return (
    <tr className="table-row">
      <td className="px-5 py-3.5">
        <p className="font-medium text-slate-950">{candidateLabel}</p>
        <p className="mt-1 text-xs text-slate-500">{invite.candidate_email ?? "Any candidate in this organization"}</p>
      </td>
      <td className="px-5 py-3.5">
        <div className="flex flex-wrap gap-2">
          <StatusBadge label={invite.status} tone={statusTone(invite.status)} />
          {invite.session_status ? <StatusBadge label={invite.session_status} tone={statusTone(invite.session_status)} /> : null}
        </div>
      </td>
      <td className="min-w-80 px-5 py-3.5">
        {invite.invite_url ? (
          <div className="flex gap-2">
            <input
              aria-label={`Invite link for ${candidateLabel}`}
              className="h-9 min-w-0 flex-1 rounded-lg border border-slate-200 bg-slate-50 px-3 text-xs text-slate-600"
              readOnly
              title={invite.invite_url}
              value={invite.invite_url}
            />
            <Button
              className="h-9 px-3 text-xs"
              disabled={!invite.invite_url || isBusy}
              onClick={() => onCopy(invite)}
              type="button"
              variant="secondary"
            >
              {isCopied ? "Copied" : "Copy"}
            </Button>
          </div>
        ) : (
          <span className="text-xs text-slate-500">Legacy link unavailable.</span>
        )}
      </td>
      <td className="whitespace-nowrap px-5 py-3.5">
        <StatusBadge
          label={invite.status === "expired" ? "Expired" : `Expires ${formatDateTime(invite.expires_at)}`}
          tone={invite.status === "expired" ? "danger" : invite.status === "active" ? "warning" : "neutral"}
        />
        {invite.used_at ? <p className="mt-1 text-xs text-slate-500">Used {formatDateTime(invite.used_at)}</p> : null}
      </td>
      <td className="px-5 py-3.5">
        <div className="flex flex-wrap gap-2">
          <Button
            className="h-9 px-3 text-xs"
            aria-busy={isBusy}
            disabled={invite.status !== "active" || isBusy}
            onClick={() => onRegenerate(invite)}
            type="button"
            variant="secondary"
          >
            Regenerate
          </Button>
          <Button
            className="h-9 px-3 text-xs"
            aria-busy={isBusy}
            disabled={invite.status !== "active" || isBusy}
            onClick={() => onRevoke(invite)}
            type="button"
            variant="danger"
          >
            Revoke
          </Button>
        </div>
      </td>
    </tr>
  );
}

type ScenarioTab = "task" | "files" | "tests" | "rubric";

function ScenarioPreview({
  scenario,
  scenarioStatus,
}: {
  scenario: Scenario;
  scenarioStatus: string;
}) {
  const [activeTab, setActiveTab] = useState<ScenarioTab>("task");
  const tabs: Array<{ id: ScenarioTab; label: string }> = [
    { id: "task", label: "Candidate task" },
    { id: "files", label: `Files (${scenario.starter_files_json.length})` },
    { id: "tests", label: `Tests (${scenario.test_files_json.length})` },
    { id: "rubric", label: "Interviewer rubric" },
  ];

  return (
    <section className="overflow-hidden rounded-card border border-white/80 bg-white shadow-panel" id="scenario-preview">
      <div className="border-b border-slate-200 px-5 py-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-blue-700">Scenario preview</p>
            <h2 className="mt-1 text-xl font-semibold text-slate-950">{scenario.title}</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{scenario.business_context}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <StatusBadge label={scenarioStatus} tone={statusTone(scenarioStatus)} />
            <StatusBadge label={scenario.language} tone="info" />
            {scenario.framework ? <StatusBadge label={scenario.framework} /> : null}
          </div>
        </div>
      </div>

      <div className="border-b border-slate-200 bg-slate-50/80 px-3 py-2">
        <div aria-label="Scenario preview sections" className="flex flex-wrap gap-1" role="tablist">
          {tabs.map((tab) => (
            <button
              aria-selected={activeTab === tab.id}
              className={
                activeTab === tab.id
                  ? "rounded-lg bg-slate-950 px-3 py-2 text-xs font-semibold text-white shadow-sm"
                  : "rounded-lg px-3 py-2 text-xs font-semibold text-slate-600 transition hover:bg-white hover:text-slate-950"
              }
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              role="tab"
              type="button"
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div className="p-5">
        {activeTab === "task" ? (
          <div className="grid gap-5">
            <section className="rounded-card border border-blue-100 bg-blue-50/50 p-5">
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge label={scenario.ai_mode} tone="info" />
                {scenario.validation_command ? (
                  <code className="rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs text-slate-700">
                    {scenario.validation_command}
                  </code>
                ) : null}
              </div>
              <h3 className="mt-4 text-base font-semibold text-slate-950">{scenario.candidate_task_summary}</h3>
              <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-700">{scenario.candidate_instructions}</p>
            </section>

            <div className="grid gap-4 lg:grid-cols-3">
              <ReviewList items={scenario.visible_requirements} title="Visible requirements" />
              <ReviewList items={scenario.constraints} title="Constraints" />
              <ReviewList items={scenario.expected_behavior} title="Expected behavior" />
            </div>

            {scenario.logs_or_bug_report ? (
              <section>
                <h3 className="text-sm font-semibold text-slate-950">Candidate-visible logs or bug report</h3>
                <pre className="mt-2 max-h-72 overflow-auto whitespace-pre-wrap rounded-lg border border-slate-800 bg-slate-950 p-4 text-xs leading-5 text-slate-300">
                  {scenario.logs_or_bug_report}
                </pre>
              </section>
            ) : null}
          </div>
        ) : null}

        {activeTab === "files" ? (
          <div className="grid gap-4">
            {scenario.project ? <ProjectFilesPreview project={scenario.project} /> : null}
            <ScenarioFilesPreview files={scenario.starter_files_json} title="Candidate-visible starter files" />
          </div>
        ) : null}

        {activeTab === "tests" ? (
          <div className="grid gap-4">
            <section className="rounded-card border border-slate-200 bg-slate-50 p-4">
              <h3 className="inline-flex items-center gap-2 text-sm font-semibold text-slate-950">
                Validation guidance
                <InfoTooltip
                  content="Candidates see the validation guidance. Hidden reviewer checks remain separate from the candidate brief."
                  label="Test validation command help"
                />
              </h3>
              <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">{scenario.validation_instructions}</p>
              {scenario.validation_command ? (
                <code className="mt-3 block w-fit rounded-md border border-slate-300 bg-white px-3 py-2 text-xs text-slate-800">
                  {scenario.validation_command}
                </code>
              ) : null}
            </section>
            <ScenarioFilesPreview files={scenario.test_files_json} title="Candidate-visible tests" />
          </div>
        ) : null}

        {activeTab === "rubric" ? (
          <div className="grid gap-5">
            <div className="rounded-card border border-amber-200 bg-amber-50 p-4">
              <p className="text-sm font-semibold text-amber-900">Interviewer-only evaluation material</p>
              <p className="mt-1 text-sm leading-6 text-amber-800">
                This section is never included in the candidate experience.
              </p>
            </div>
            <section className="rounded-card border border-slate-200 bg-slate-50 p-4">
              <h3 className="text-sm font-semibold text-slate-950">Expected solution summary</h3>
              <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">{scenario.expected_solution_summary}</p>
            </section>
            <div className="grid gap-4 lg:grid-cols-3">
              <ReviewList items={scenario.hidden_evaluation_points} title="Hidden evaluation points" />
              <ReviewList items={scenario.hidden_rubric} title="Hidden rubric" />
              <ReviewList items={scenario.interviewer_rubric} title="Interviewer rubric" />
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}

function InterviewDetailContent() {
  const params = useParams<{ interviewId: string }>();
  const router = useRouter();
  const { token, user } = useAuth();
  const [interview, setInterview] = useState<Interview | null>(null);
  const [submissions, setSubmissions] = useState<InterviewSubmissionResult[]>([]);
  const [invites, setInvites] = useState<InviteTokenResponse[]>([]);
  const [inviteEmail, setInviteEmail] = useState(DEFAULT_INVITE_EMAIL);
  const [inviteName, setInviteName] = useState(DEFAULT_INVITE_NAME);
  const [inviteExpiryDays, setInviteExpiryDays] = useState(DEFAULT_INVITE_DAYS);
  const [inviteCount, setInviteCount] = useState(DEFAULT_INVITE_COUNT);
  const [isLoading, setIsLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isCreatingInvite, setIsCreatingInvite] = useState(false);
  const [copiedInviteId, setCopiedInviteId] = useState<string | null>(null);
  const [busyInviteId, setBusyInviteId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const canManageInterviews = user?.role === "ADMIN" || user?.role === "INTERVIEWER";
  const readyReviewCount = submissions.filter((submission) =>
    ["submitted", "ready_for_review"].includes(submission.status),
  ).length;
  const activeInviteCount = invites.filter((invite) => invite.status === "active").length;
  const scenarioStatus = interview?.scenario?.status ?? "draft";
  const scenarioReady = scenarioStatus === "approved";

  useEffect(() => {
    if (!token || !params.interviewId || !canManageInterviews) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    Promise.all([
      getInterview(token, params.interviewId),
      getInterviewSubmissions(token, params.interviewId),
      getInterviewInvites(token, params.interviewId),
    ])
      .then(([loadedInterview, loadedSubmissions, loadedInvites]) => {
        setInterview(loadedInterview);
        setSubmissions(loadedSubmissions);
        setInvites(loadedInvites);
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
      setInterview({ ...interview, scenario, status: "SCENARIO_GENERATED" });
      setSuccessMessage("Scenario generated. Review and approve it before inviting candidates.");
    } catch (requestError: unknown) {
      const message = requestError instanceof ApiError ? requestError.message : "Unable to generate scenario.";
      setError(message);
    } finally {
      setIsGenerating(false);
    }
  }

  async function handleApproveScenario() {
    if (!token || !interview?.scenario) {
      return;
    }
    setIsApproving(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const scenario = await approveScenario(token, interview.id);
      setInterview({ ...interview, scenario, status: "READY" });
      setSuccessMessage("Scenario approved. Candidate invites can now be created and started.");
    } catch (requestError: unknown) {
      const message = requestError instanceof ApiError ? requestError.message : "Unable to approve scenario.";
      setError(message);
    } finally {
      setIsApproving(false);
    }
  }

  async function handleCreateInvite() {
    if (!token || !interview) {
      return;
    }
    if (!scenarioReady) {
      setError("Approve the generated scenario before creating invites.");
      return;
    }
    const candidateEmail = inviteEmail.trim();
    const candidateName = inviteName.trim();
    if (candidateEmail && inviteCount !== 1) {
      setError("Candidate-specific invites must be generated one at a time.");
      return;
    }

    setIsCreatingInvite(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const response = await createCandidateInvite(token, interview.id, {
        candidate_email: candidateEmail || null,
        candidate_name: candidateName || null,
        expires_in_days: inviteExpiryDays,
        invite_count: inviteCount,
      });
      setInvites((currentInvites) => [...response.invites, ...currentInvites]);
      setInviteEmail(DEFAULT_INVITE_EMAIL);
      setInviteName(DEFAULT_INVITE_NAME);
      setInviteCount(DEFAULT_INVITE_COUNT);
      setSuccessMessage(response.invites.length === 1 ? "Invite link created." : `${response.invites.length} invite links created.`);
    } catch (requestError: unknown) {
      const message = requestError instanceof ApiError ? requestError.message : "Unable to create invite.";
      setError(message);
    } finally {
      setIsCreatingInvite(false);
    }
  }

  async function handleCopyInvite(invite: InviteTokenResponse) {
    if (!invite.invite_url) {
      return;
    }
    try {
      await navigator.clipboard.writeText(invite.invite_url);
      setCopiedInviteId(invite.id);
      window.setTimeout(() => setCopiedInviteId(null), 1500);
    } catch {
      setCopiedInviteId(null);
    }
  }

  async function handleRegenerateInvite(invite: InviteTokenResponse) {
    if (!token || !interview) {
      return;
    }
    setBusyInviteId(invite.id);
    setError(null);
    setSuccessMessage(null);
    try {
      const replacement = await regenerateInterviewInvite(token, interview.id, invite.id, { expires_in_days: inviteExpiryDays });
      setInvites((currentInvites) => [
        replacement,
        ...currentInvites.map((item) =>
          item.id === invite.id ? { ...item, status: "revoked" as const, revoked_at: new Date().toISOString() } : item,
        ),
      ]);
      setSuccessMessage("Invite regenerated. The old link has been revoked.");
    } catch (requestError: unknown) {
      const message = requestError instanceof ApiError ? requestError.message : "Unable to regenerate invite.";
      setError(message);
    } finally {
      setBusyInviteId(null);
    }
  }

  async function handleRevokeInvite(invite: InviteTokenResponse) {
    if (!token || !interview) {
      return;
    }
    setBusyInviteId(invite.id);
    setError(null);
    setSuccessMessage(null);
    try {
      const revoked = await revokeInterviewInvite(token, interview.id, invite.id);
      setInvites((currentInvites) => currentInvites.map((item) => (item.id === invite.id ? revoked : item)));
      setSuccessMessage("Invite revoked.");
    } catch (requestError: unknown) {
      const message = requestError instanceof ApiError ? requestError.message : "Unable to revoke invite.";
      setError(message);
    } finally {
      setBusyInviteId(null);
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
              <ActionButton href="/interviews" variant="secondary">
                Back to interviews
              </ActionButton>
              <Button aria-busy={isDeleting} disabled={isDeleting} onClick={() => void handleDeleteInterview()} type="button" variant="danger">
                {isDeleting ? "Deleting..." : "Delete interview"}
              </Button>
            </>
          ) : null
        }
        description={
          interview
            ? `${interview.seniority} / ${interview.interview_type} / ${interview.duration_minutes} minutes / created ${formatDateTime(interview.created_at)}`
            : "Review scenario readiness, invite candidates, and track session outcomes."
        }
        eyebrow="Interview control center"
        meta={
          interview ? (
            <>
              <StatusBadge label={interview.status} tone={statusTone(interview.status)} />
              <StatusBadge label={`Scenario: ${scenarioStatus}`} tone={statusTone(scenarioStatus)} />
              <StatusBadge label={interview.difficulty} />
              <StatusBadge label={interview.allowed_ai_mode} tone="info" />
              {interview.stack.slice(0, 3).map((item) => (
                <StatusBadge key={item} label={item} />
              ))}
            </>
          ) : null
        }
        title={interview?.role_title ?? "Interview details"}
      />

      <section className="mt-5 grid gap-4">
        {isLoading ? <LoadingState label="Loading interview" rows={4} /> : null}
        {error ? <ErrorState message={error} /> : null}
        {successMessage ? (
          <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700" role="status">
            {successMessage}
          </p>
        ) : null}

        {interview ? (
          <>
            <section className="grid gap-4 xl:grid-cols-[0.75fr_1.25fr]">
              <section className="rounded-card border border-white/80 bg-white p-5 shadow-panel">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Scenario readiness</p>
                    <h2 className="mt-2 text-xl font-semibold text-slate-950">
                      {interview.scenario?.title ?? "Scenario not generated"}
                    </h2>
                  </div>
                  <StatusBadge label={scenarioStatus} tone={statusTone(scenarioStatus)} />
                </div>
                <p className="mt-3 text-sm leading-6 text-slate-600">
                  {scenarioReady
                    ? "Approved for candidate invites and session starts."
                    : interview.scenario
                      ? "Review the task, tests, and hidden rubric before approval."
                      : "Generate a stack-matched scenario before creating candidate access."}
                </p>
                <dl className="mt-5 grid grid-cols-3 border-y border-slate-200 py-4 text-center">
                  <div>
                    <dt className="text-xs text-slate-500">Active invites</dt>
                    <dd className="mt-1 text-xl font-semibold text-slate-950">{activeInviteCount}</dd>
                  </div>
                  <div className="border-x border-slate-200">
                    <dt className="text-xs text-slate-500">Sessions</dt>
                    <dd className="mt-1 text-xl font-semibold text-slate-950">{submissions.length}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-slate-500">Ready to review</dt>
                    <dd className="mt-1 text-xl font-semibold text-slate-950">{readyReviewCount}</dd>
                  </div>
                </dl>
                <div className="mt-5 flex flex-wrap gap-2">
                  <Button
                    aria-busy={isGenerating}
                    disabled={isGenerating}
                    onClick={() => void handleGenerateScenario()}
                    type="button"
                    variant="secondary"
                  >
                    {isGenerating ? "Generating..." : interview.scenario ? "Regenerate scenario" : "Generate scenario"}
                  </Button>
                  <Button
                    aria-busy={isApproving}
                    disabled={isApproving || !interview.scenario || scenarioReady}
                    onClick={() => void handleApproveScenario()}
                    type="button"
                  >
                    {isApproving ? "Approving..." : scenarioReady ? "Approved" : "Approve scenario"}
                  </Button>
                  {interview.scenario ? (
                    <ActionButton href="#scenario-preview" variant="ghost">
                      Review scenario
                    </ActionButton>
                  ) : null}
                </div>
              </section>

              <section className="rounded-card border border-white/80 bg-white p-5 shadow-panel" id="invite-composer">
                <SectionHeader
                  aside={<StatusBadge label={`${activeInviteCount} active`} tone={activeInviteCount ? "success" : "neutral"} />}
                  description="Create candidate-specific access or a small batch of generic, single-use links."
                  title="Create candidate invite"
                />
                <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                  <Input
                    id="candidate_invite_name"
                    label="Candidate name"
                    onChange={(event) => setInviteName(event.target.value)}
                    placeholder="Optional"
                    type="text"
                    value={inviteName}
                  />
                  <Input
                    id="candidate_invite_email"
                    label="Candidate invite email"
                    onChange={(event) => setInviteEmail(event.target.value)}
                    placeholder="Optional for generic links"
                    type="email"
                    value={inviteEmail}
                  />
                  <Input
                    id="candidate_invite_expiry"
                    label="Expires in days"
                    max={60}
                    min={1}
                    onChange={(event) => setInviteExpiryDays(Number(event.target.value) || DEFAULT_INVITE_DAYS)}
                    type="number"
                    value={inviteExpiryDays}
                  />
                  <Input
                    id="candidate_invite_count"
                    label="Number of links"
                    max={25}
                    min={1}
                    onChange={(event) => setInviteCount(Number(event.target.value) || DEFAULT_INVITE_COUNT)}
                    type="number"
                    value={inviteCount}
                  />
                </div>
                <div className="mt-4 flex flex-col gap-3 border-t border-slate-200 pt-4 sm:flex-row sm:items-center sm:justify-between">
                  {!interview.scenario ? (
                    <p className="text-xs text-slate-500">Generate the scenario before creating an invite.</p>
                  ) : !scenarioReady ? (
                    <p className="text-xs text-amber-700">Approve the generated scenario before creating candidate links.</p>
                  ) : (
                    <p className="text-xs text-slate-500">
                      Leave email blank to create generic single-use links for candidates in this organization.
                    </p>
                  )}
                  <Button
                    className="shrink-0"
                    aria-busy={isCreatingInvite}
                    disabled={isCreatingInvite || !scenarioReady}
                    onClick={() => void handleCreateInvite()}
                    type="button"
                  >
                    {isCreatingInvite ? "Creating..." : "Create invite"}
                  </Button>
                </div>
              </section>
            </section>

            <section className="overflow-hidden rounded-card border border-white/80 bg-white shadow-panel">
              <div className="border-b border-slate-200 px-5 py-4">
                <SectionHeader
                  aside={<span className="text-xs uppercase tracking-wide text-slate-500">{invites.length} invites</span>}
                  description="Active and historical access links with expiry and lifecycle controls."
                  title="Invite management"
                />
              </div>
              {invites.length === 0 ? (
                <EmptyState
                  actionHref="#invite-composer"
                  actionLabel="Create invite"
                  description="Create a candidate-specific or generic link after the scenario is approved."
                  embedded
                  title="No invites yet"
                />
              ) : (
                <div className="overflow-x-auto">
                  <table className="table-surface">
                    <thead className="table-head">
                      <tr>
                        <th className="px-5 py-3 font-medium">Candidate</th>
                        <th className="px-5 py-3 font-medium">Status</th>
                        <th className="px-5 py-3 font-medium">Invite URL</th>
                        <th className="px-5 py-3 font-medium">Expiry</th>
                        <th className="px-5 py-3 font-medium">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200">
                      {invites.map((invite) => (
                        <InviteRow
                          invite={invite}
                          isBusy={busyInviteId === invite.id}
                          isCopied={copiedInviteId === invite.id}
                          key={invite.id}
                          onCopy={(item) => void handleCopyInvite(item)}
                          onRegenerate={(item) => void handleRegenerateInvite(item)}
                          onRevoke={(item) => void handleRevokeInvite(item)}
                        />
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            <section className="overflow-hidden rounded-card border border-white/80 bg-white shadow-panel">
              <div className="border-b border-slate-200 px-5 py-4">
                <SectionHeader
                  aside={<span className="text-xs uppercase tracking-wide text-slate-500">{submissions.length} sessions</span>}
                  description="Candidate activity and result readiness for this interview."
                  title="Candidate sessions"
                />
              </div>
              {submissions.length === 0 ? (
                <EmptyState
                  actionHref="#invite-composer"
                  actionLabel="Create invite"
                  description="Candidate activity and review readiness will appear after an invite is used."
                  embedded
                  title="No candidate sessions yet"
                />
              ) : (
                <div className="overflow-x-auto">
                  <table className="table-surface">
                    <thead className="table-head">
                      <tr>
                        <th className="px-5 py-3 font-medium">Candidate</th>
                        <th className="px-5 py-3 font-medium">Status</th>
                        <th className="px-5 py-3 font-medium">Timeline</th>
                        <th className="px-5 py-3 font-medium">Result</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200">
                      {submissions.map((submission) => (
                        <CandidateSessionRow key={submission.session_id} submission={submission} />
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            {interview.scenario ? <ScenarioPreview scenario={interview.scenario} scenarioStatus={scenarioStatus} /> : (
              <EmptyState
                action={
                  <Button
                    aria-busy={isGenerating}
                    disabled={isGenerating}
                    onClick={() => void handleGenerateScenario()}
                    type="button"
                  >
                    {isGenerating ? "Generating..." : "Generate scenario"}
                  </Button>
                }
                description="Generate the scenario to review the task, files, tests, and interviewer-only rubric."
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
