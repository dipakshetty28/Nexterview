import type { AuthResponse, DashboardResponse, Interview, InterviewInput, InterviewListResponse, User } from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type ApiRequestOptions = {
  method?: "DELETE" | "GET" | "PATCH" | "POST";
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

  if (response.status === 204) {
    return undefined as T;
  }

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail =
      typeof payload?.detail === "string"
        ? payload.detail
        : Array.isArray(payload?.detail)
          ? payload.detail.map((item: { msg?: string }) => item.msg).filter(Boolean).join(" ")
          : "Request failed.";
    throw new ApiError(detail, response.status);
  }

  return payload as T;
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

export function listInterviews(token: string): Promise<InterviewListResponse> {
  return apiRequest<InterviewListResponse>("/api/interviews", { token });
}

export function createInterview(token: string, input: InterviewInput): Promise<Interview> {
  return apiRequest<Interview>("/api/interviews", {
    method: "POST",
    body: input,
    token,
  });
}

export function getInterview(token: string, interviewId: string): Promise<Interview> {
  return apiRequest<Interview>(`/api/interviews/${interviewId}`, { token });
}

export function deleteInterview(token: string, interviewId: string): Promise<void> {
  return apiRequest<void>(`/api/interviews/${interviewId}`, {
    method: "DELETE",
    token,
  });
}
