"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/app/app-shell";
import {
  EmptyState,
  ErrorState,
  FloatingHint,
  InfoTooltip,
  LoadingState,
  PageHeader,
  SectionHeader,
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
        <div className="grid gap-1 text-xs text-slate-600 md:text-right">
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
      <td className="px-5 py-4">
        <p className="font-medium text-slate-950">{submission.candidate_name}</p>
        <p className="mt-1 text-xs text-slate-500">{submission.candidate_email}</p>
      </td>
      <td className="px-5 py-4">
        <StatusBadge label={submission.status} tone={statusTone(submission.status)} />
      </td>
      <td className="px-5 py-4">
        {submission.invite_status ? (
          <StatusBadge label={submission.invite_status} tone={statusTone(submission.invite_status)} />
        ) : (
          <span className="text-slate-600">No invite</span>
        )}
      </td>
      <td className="px-5 py-4 text-slate-600">{formatDateTime(submission.started_at)}</td>
      <td className="px-5 py-4 text-slate-600">{formatDateTime(submission.submitted_at)}</td>
      <td className="px-5 py-4 text-slate-700">{submission.test_output ? "Test output submitted" : "No test output"}</td>
      <td className="px-5 py-4">
        {submission.submission_id ? (
          <Link className="font-semibold text-blue-700 hover:text-blue-900" href={`/results/${submission.session_id}`}>
            View result
          </Link>
        ) : (
          <span className="text-slate-600">Pending submission</span>
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
      <td className="px-5 py-4">
        <p className="font-medium text-slate-950">{candidateLabel}</p>
        <p className="mt-1 text-xs text-slate-500">{invite.candidate_email ?? "Any candidate in this organization"}</p>
      </td>
      <td className="px-5 py-4">
        <StatusBadge label={invite.status} tone={statusTone(invite.status)} />
      </td>
      <td className="px-5 py-4 text-slate-600">{formatDateTime(invite.expires_at)}</td>
      <td className="px-5 py-4 text-slate-600">{formatDateTime(invite.used_at)}</td>
      <td className="max-w-sm px-5 py-4">
        {invite.invite_url ? (
          <p className="break-all rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-blue-700">
            {invite.invite_url}
          </p>
        ) : (
          <span className="text-xs text-slate-500">Legacy link unavailable.</span>
        )}
      </td>
      <td className="px-5 py-4">
        <div className="flex flex-wrap gap-2">
          <Button aria-busy={isBusy} disabled={!invite.invite_url || isBusy} onClick={() => onCopy(invite)} type="button" variant="ghost">
            {isCopied ? "Copied" : "Copy"}
          </Button>
          <Button aria-busy={isBusy} disabled={invite.status !== "active" || isBusy} onClick={() => onRegenerate(invite)} type="button" variant="secondary">
            Regenerate
          </Button>
          <Button aria-busy={isBusy} disabled={invite.status !== "active" || isBusy} onClick={() => onRevoke(invite)} type="button" variant="ghost">
            Revoke
          </Button>
        </div>
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
  const submittedCount = submissions.filter((submission) =>
    ["submitted", "ready_for_review", "review_in_progress", "reviewed", "review_failed"].includes(submission.status),
  ).length;
  const reviewedCount = submissions.filter((submission) => submission.status === "reviewed").length;
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
              <Button aria-busy={isGenerating} disabled={isGenerating} onClick={() => void handleGenerateScenario()} type="button">
                {isGenerating ? "Generating..." : interview.scenario ? "Regenerate scenario" : "Generate scenario"}
              </Button>
              <Button
                aria-busy={isApproving}
                disabled={isApproving || !interview.scenario || scenarioReady}
                onClick={() => void handleApproveScenario()}
                type="button"
                variant="secondary"
              >
                {isApproving ? "Approving..." : scenarioReady ? "Scenario approved" : "Approve scenario"}
              </Button>
              <Button aria-busy={isDeleting} disabled={isDeleting} onClick={() => void handleDeleteInterview()} type="button" variant="danger">
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
        {isLoading ? <LoadingState label="Loading interview" rows={4} /> : null}
        {error ? <ErrorState message={error} /> : null}
        {successMessage ? (
          <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
            {successMessage}
          </p>
        ) : null}

        {interview ? (
          <>
            <section className="grid gap-4 lg:grid-cols-4">
              <StatCard description={`${interview.seniority} / ${interview.difficulty}`} label="Role" value={interview.role_title} />
              <StatCard description={interview.interview_type} label="Duration" value={`${interview.duration_minutes} min`} />
              <StatCard
                description={scenarioReady ? "Candidates can start approved invites." : "Review and approve before inviting."}
                label="Scenario status"
                tone={statusTone(scenarioStatus)}
                value={scenarioStatus}
              />
              <StatCard description={`${submittedCount} submitted, ${reviewedCount} reviewed`} label="Candidate sessions" value={submissions.length} />
            </section>

            <section className="rounded-card border border-white/80 bg-white p-5 shadow-panel">
              <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge label={interview.status} tone={statusTone(interview.status)} />
                    <StatusBadge label={`Scenario: ${scenarioStatus}`} tone={statusTone(scenarioStatus)} />
                    <StatusBadge label={interview.allowed_ai_mode} tone="info" />
                  </div>
                  <h2 className="mt-3 text-lg font-semibold text-slate-950">{interview.role_title}</h2>
                  <p className="mt-2 text-sm leading-6 text-slate-600">
                    Created {formatDateTime(interview.created_at)}. Stack: {interview.stack.join(", ")}
                  </p>
                </div>

                <div className="grid w-full gap-3 xl:w-[28rem]">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold text-slate-950">Candidate invite</p>
                    <InfoTooltip content="Invite links remain visible here with expiry, usage, regeneration, and revocation status." label="Invite expiry help" />
                  </div>
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
                  <div className="grid gap-3 sm:grid-cols-2">
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
                  <div className="flex flex-col gap-2 sm:flex-row">
                    <Button
                      className="flex-1"
                      aria-busy={isCreatingInvite}
                      disabled={isCreatingInvite || !scenarioReady}
                      onClick={() => void handleCreateInvite()}
                      type="button"
                      variant="secondary"
                    >
                      {isCreatingInvite ? "Creating invite..." : "Create invite"}
                    </Button>
                  </div>
                  {!interview.scenario ? (
                    <p className="text-xs text-slate-500">Generate the scenario before creating an invite.</p>
                  ) : !scenarioReady ? (
                    <p className="text-xs text-amber-700">Approve the generated scenario before creating candidate links.</p>
                  ) : (
                    <p className="text-xs text-slate-500">
                      Leave email blank to create generic single-use links for candidates in this organization.
                    </p>
                  )}
                </div>
              </div>
            </section>

            <section className="overflow-hidden rounded-card border border-white/80 bg-white shadow-panel">
              <div className="border-b border-slate-200 px-5 py-4">
                <SectionHeader
                  aside={<span className="text-xs uppercase tracking-wide text-slate-500">{invites.length} invites</span>}
                  description="Persistent candidate links with status, expiry, and regeneration controls."
                  title="Invite links"
                />
              </div>
              {invites.length === 0 ? (
                <div className="p-5">
                  <EmptyState
                    description="Create a candidate-specific or generic invite. Existing links will remain visible here when you reopen the interview."
                    title="No invites yet"
                  />
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="table-surface">
                    <thead className="table-head">
                      <tr>
                        <th className="px-5 py-3 font-medium">Candidate</th>
                        <th className="px-5 py-3 font-medium">Status</th>
                        <th className="px-5 py-3 font-medium">Expires</th>
                        <th className="px-5 py-3 font-medium">Used</th>
                        <th className="px-5 py-3 font-medium">Invite URL</th>
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
                <div className="p-5">
                  <EmptyState
                    description="Create an invite and share it with a candidate. Sessions will appear here after invite use."
                    title="No candidate sessions yet"
                  />
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="table-surface">
                    <thead className="table-head">
                      <tr>
                        <th className="px-5 py-3 font-medium">Candidate</th>
                        <th className="px-5 py-3 font-medium">Session</th>
                        <th className="px-5 py-3 font-medium">Invite</th>
                        <th className="px-5 py-3 font-medium">Started</th>
                        <th className="px-5 py-3 font-medium">Submitted</th>
                        <th className="px-5 py-3 font-medium">Validation</th>
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

            {interview.scenario ? (
              <section className="grid gap-5 rounded-card border border-white/80 bg-white p-5 shadow-panel">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <p className="text-sm font-medium text-blue-700">Scenario preview</p>
                    <h2 className="mt-1 text-xl font-semibold text-slate-950">{interview.scenario.title}</h2>
                    <p className="mt-2 text-sm leading-6 text-slate-600">{interview.scenario.business_context}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <StatusBadge label={scenarioStatus} tone={statusTone(scenarioStatus)} />
                    <StatusBadge label="Reviewer visible" tone="info" />
                  </div>
                </div>

                <FloatingHint title="Scenario quality gate" tone={scenarioReady ? "success" : "warning"}>
                  {scenarioReady
                    ? "This scenario is approved, so candidate invite links can be created and started."
                    : "Review the candidate-visible brief, validation guidance, and hidden rubric before approving this scenario."}
                </FloatingHint>

                <div className="grid gap-4 lg:grid-cols-2">
                  <ReviewList items={interview.scenario.visible_requirements} title="Visible requirements" />
                  <ReviewList items={interview.scenario.constraints} title="Candidate constraints" />
                  <ReviewList items={interview.scenario.expected_behavior} title="Expected behavior" />
                  <ReviewList items={interview.scenario.hidden_evaluation_points} title="Hidden evaluation points" />
                  <ReviewList items={interview.scenario.hidden_rubric} title="Hidden rubric" />
                  <ReviewList items={interview.scenario.interviewer_rubric} title="Interviewer rubric" />
                </div>

                <section className="grid gap-3 rounded-card border border-slate-200 bg-slate-50/90 p-4">
                  <h3 className="text-sm font-semibold text-slate-950">Candidate-facing brief</h3>
                  <p className="whitespace-pre-wrap text-sm leading-6 text-slate-700">{interview.scenario.candidate_instructions}</p>
                  <div className="grid gap-3 text-sm leading-6 text-slate-700 md:grid-cols-2">
                    <p>
                      <span className="font-medium text-slate-950">Bug:</span> {interview.scenario.bug_description}
                    </p>
                    <p>
                      <span className="font-medium text-slate-950">Feature:</span> {interview.scenario.feature_request}
                    </p>
                  </div>
                  {interview.scenario.logs_or_bug_report ? (
                    <pre className="max-h-72 overflow-auto whitespace-pre-wrap rounded-md border border-slate-800 bg-slate-950 p-3 text-xs leading-5 text-slate-300">
                      {interview.scenario.logs_or_bug_report}
                    </pre>
                  ) : null}
                </section>

                <section>
                  <h3 className="inline-flex items-center gap-2 text-sm font-semibold text-slate-950">
                    Validation instructions
                    <InfoTooltip content="Candidates see the validation guidance, but the platform owns the actual pass/fail runner and hidden reviewer context." label="Test validation command help" />
                  </h3>
                  <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-600">
                    {interview.scenario.validation_instructions}
                  </p>
                </section>

                <section className="grid gap-3 rounded-card border border-slate-200 bg-slate-50/90 p-4">
                  <h3 className="text-sm font-semibold text-slate-950">Expected solution summary</h3>
                  <p className="whitespace-pre-wrap text-sm leading-6 text-slate-700">{interview.scenario.expected_solution_summary}</p>
                </section>

                {interview.scenario.project ? <ProjectFilesPreview project={interview.scenario.project} /> : null}
                <div className="grid gap-4 lg:grid-cols-2">
                  <ScenarioFilesPreview files={interview.scenario.starter_files_json} title="Candidate-visible starter files" />
                  <ScenarioFilesPreview files={interview.scenario.test_files_json} title="Candidate-visible tests" />
                </div>
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
