import type {
  AuthResponse,
  AICopilotResponse,
  CalibrationSession,
  CandidateWorkspace,
  CandidateSession,
  DashboardResponse,
  Interview,
  InterviewCreateInput,
  InterviewSubmissionResult,
  InviteCreateResponse,
  InviteTokenResponse,
  PublicInvite,
  ResultsDashboardItem,
  Scenario,
  SessionResult,
  Submission,
  SubmissionReviewSummary,
  TelemetryEvent,
  TelemetryEventType,
  TestRunResult,
  User,
  WorkspaceFile,
} from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type ApiRequestOptions = {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: unknown;
  token?: string;
};

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number, options?: ErrorOptions) {
    super(message, options);
    this.name = "ApiError";
    this.status = status;
  }
}

async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  if (options.token) {
    headers.Authorization = `Bearer ${options.token}`;
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: options.method ?? "GET",
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      cache: "no-store",
    });
  } catch (error) {
    throw new ApiError(`Unable to reach the API at ${API_BASE_URL}.`, 0, { cause: error });
  }

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = typeof payload?.detail === "string" ? payload.detail : "Request failed.";
    throw new ApiError(detail, response.status);
  }

  return payload as T;
}

function assertInterviewList(payload: unknown): Interview[] {
  if (Array.isArray(payload)) {
    return payload as Interview[];
  }
  throw new ApiError("Unexpected response while loading interviews.", 502);
}

export function registerAccount(input: {
  email: string;
  password: string;
  full_name: string;
  organization_name: string;
}): Promise<AuthResponse> {
  return apiRequest<AuthResponse>("/api/auth/register", {
    method: "POST",
    body: input,
  });
}

export function loginAccount(input: { email: string; password: string }): Promise<AuthResponse> {
  return apiRequest<AuthResponse>("/api/auth/login", {
    method: "POST",
    body: input,
  });
}

export function getCurrentUser(token: string): Promise<User> {
  return apiRequest<User>("/api/auth/me", { token });
}

export function getDashboard(token: string): Promise<DashboardResponse> {
  return apiRequest<DashboardResponse>("/api/dashboard", { token });
}

export async function getInterviews(token: string): Promise<Interview[]> {
  const payload = await apiRequest<unknown>("/api/interviews", { token });
  return assertInterviewList(payload);
}

export function createInterview(token: string, input: InterviewCreateInput): Promise<Interview> {
  return apiRequest<Interview>("/api/interviews", {
    method: "POST",
    token,
    body: input,
  });
}

export function getInterview(token: string, interviewId: string): Promise<Interview> {
  return apiRequest<Interview>(`/api/interviews/${interviewId}`, { token });
}

export function getInterviewSubmissions(token: string, interviewId: string): Promise<InterviewSubmissionResult[]> {
  return apiRequest<InterviewSubmissionResult[]>(`/api/interviews/${interviewId}/submissions`, { token });
}

export function getSessionResult(token: string, sessionId: string): Promise<SessionResult> {
  return apiRequest<SessionResult>(`/api/results/${sessionId}`, { token });
}

export function getResultsDashboard(token: string): Promise<ResultsDashboardItem[]> {
  return apiRequest<ResultsDashboardItem[]>("/api/results", { token });
}

export function getCalibrationSessions(token: string): Promise<CalibrationSession[]> {
  return apiRequest<CalibrationSession[]>("/api/calibration", { token });
}

export function runSubmissionReview(token: string, submissionId: string): Promise<SubmissionReviewSummary> {
  return apiRequest<SubmissionReviewSummary>(`/api/submissions/${submissionId}/review`, {
    method: "POST",
    token,
  });
}

export function deleteInterview(token: string, interviewId: string): Promise<void> {
  return apiRequest<void>(`/api/interviews/${interviewId}`, {
    method: "DELETE",
    token,
  });
}

export function generateScenario(token: string, interviewId: string): Promise<Scenario> {
  return apiRequest<Scenario>(`/api/interviews/${interviewId}/generate-scenario`, {
    method: "POST",
    token,
  });
}

export function approveScenario(token: string, interviewId: string): Promise<Scenario> {
  return apiRequest<Scenario>(`/api/interviews/${interviewId}/scenario/approve`, {
    method: "POST",
    token,
  });
}

export function createCandidateInvite(
  token: string,
  interviewId: string,
  input: { candidate_email?: string | null; candidate_name?: string | null; expires_in_days?: number; invite_count?: number },
): Promise<InviteCreateResponse> {
  return apiRequest<InviteCreateResponse>(`/api/interviews/${interviewId}/invite`, {
    method: "POST",
    token,
    body: input,
  });
}

export function getInterviewInvites(token: string, interviewId: string): Promise<InviteTokenResponse[]> {
  return apiRequest<InviteTokenResponse[]>(`/api/interviews/${interviewId}/invites`, { token });
}

export function regenerateInterviewInvite(
  token: string,
  interviewId: string,
  inviteId: string,
  input: { expires_in_days?: number },
): Promise<InviteTokenResponse> {
  return apiRequest<InviteTokenResponse>(`/api/interviews/${interviewId}/invites/${inviteId}/regenerate`, {
    method: "POST",
    token,
    body: input,
  });
}

export function revokeInterviewInvite(token: string, interviewId: string, inviteId: string): Promise<InviteTokenResponse> {
  return apiRequest<InviteTokenResponse>(`/api/interviews/${interviewId}/invites/${inviteId}/revoke`, {
    method: "POST",
    token,
  });
}

export function getInvite(inviteToken: string): Promise<PublicInvite> {
  return apiRequest<PublicInvite>(`/api/invite/${inviteToken}`);
}

export function startInviteSession(token: string, inviteToken: string): Promise<CandidateSession> {
  return apiRequest<CandidateSession>(`/api/invite/${inviteToken}/start`, {
    method: "POST",
    token,
  });
}

export function getCandidateSession(token: string, sessionId: string): Promise<CandidateSession> {
  return apiRequest<CandidateSession>(`/api/sessions/${sessionId}`, { token });
}

export function getCandidateWorkspace(token: string, sessionId: string): Promise<CandidateWorkspace> {
  return apiRequest<CandidateWorkspace>(`/api/sessions/${sessionId}/workspace`, { token });
}

export function updateWorkspaceFile(
  token: string,
  sessionId: string,
  fileId: string,
  input: { content: string },
): Promise<WorkspaceFile> {
  return apiRequest<WorkspaceFile>(`/api/sessions/${sessionId}/files/${fileId}`, {
    method: "PUT",
    token,
    body: input,
  });
}

export function askCandidateCopilot(
  token: string,
  sessionId: string,
  input: {
    question: string;
    code?: string;
    current_file_path?: string | null;
    current_file_content?: string | null;
    latest_test_output?: string | null;
    notes?: string | null;
  },
): Promise<AICopilotResponse> {
  return apiRequest<AICopilotResponse>(`/api/sessions/${sessionId}/ai`, {
    method: "POST",
    token,
    body: input,
  });
}

export function saveSessionEvent(
  token: string,
  sessionId: string,
  input: { event_type: TelemetryEventType; payload?: Record<string, unknown> },
): Promise<TelemetryEvent> {
  return apiRequest<TelemetryEvent>(`/api/sessions/${sessionId}/events`, {
    method: "POST",
    token,
    body: { event_type: input.event_type, payload: input.payload ?? {} },
  });
}

export function runSessionTests(token: string, sessionId: string, input: { code?: string } = {}): Promise<TestRunResult> {
  return apiRequest<TestRunResult>(`/api/sessions/${sessionId}/run-tests`, {
    method: "POST",
    token,
    body: input,
  });
}

export function submitSessionSolution(
  token: string,
  sessionId: string,
  input: {
    code?: string;
    notes: string;
    test_output?: string | null;
    submitted_files?: Array<{ path: string; content: string; language: string; file_type?: string | null }>;
  },
): Promise<Submission> {
  return apiRequest<Submission>(`/api/sessions/${sessionId}/submit`, {
    method: "POST",
    token,
    body: input,
  });
}
