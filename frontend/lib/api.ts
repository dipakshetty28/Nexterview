import type { AuthResponse, DashboardResponse, Interview, InterviewCreateInput, Scenario, User } from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type ApiRequestOptions = {
  method?: "GET" | "POST";
  body?: unknown;
  token?: string;
};

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
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

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    cache: "no-store",
  });

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

export function generateScenario(token: string, interviewId: string): Promise<Scenario> {
  return apiRequest<Scenario>(`/api/interviews/${interviewId}/generate-scenario`, {
    method: "POST",
    token,
  });
}
