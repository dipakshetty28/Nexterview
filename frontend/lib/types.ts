export type UserRole = "ADMIN" | "INTERVIEWER" | "CANDIDATE";

export type Organization = {
  id: string;
  name: string;
  slug: string;
};

export type OrganizationMembership = {
  role: UserRole;
  organization: Organization;
};

export type User = {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  organizations: OrganizationMembership[];
};

export type AuthResponse = {
  access_token: string;
  token_type: "bearer";
  user: User;
};

export type DashboardResponse = {
  user: User;
  organizations: OrganizationMembership[];
};

export type Scenario = {
  id: string;
  interview_id: string;
  title: string;
  business_context: string;
  technical_requirements: string[];
  starter_code: string;
  expected_behavior: string[];
  logs_or_bug_report: string;
  hidden_evaluation_points: string[];
  candidate_instructions: string;
  interviewer_rubric: string[];
  generation_source: string;
  ai_model: string | null;
  created_at: string;
  updated_at: string;
};

export type Interview = {
  id: string;
  organization_id: string;
  created_by_id: string | null;
  role_title: string;
  seniority: string;
  stack: string[];
  difficulty: string;
  interview_type: string;
  duration_minutes: number;
  allowed_ai_mode: string;
  evaluation_criteria: string[];
  status: string;
  created_at: string;
  updated_at: string;
  scenario: Scenario | null;
};

export type InterviewCreateInput = {
  role_title: string;
  seniority: string;
  stack: string[];
  difficulty: string;
  interview_type: string;
  duration_minutes: number;
  allowed_ai_mode: string;
  evaluation_criteria: string[];
};

export type InviteTokenResponse = {
  id: string;
  interview_id: string;
  session_id: string;
  candidate_email: string;
  invite_url: string;
  expires_at: string;
  used_at: string | null;
};

export type PublicInvite = {
  interview: {
    id: string;
    role_title: string;
    seniority: string;
    stack: string[];
    difficulty: string;
    interview_type: string;
    duration_minutes: number;
    allowed_ai_mode: string;
    scenario_title: string | null;
  };
  candidate_email: string;
  expires_at: string;
  status: "invited" | "started" | "submitted" | "reviewed";
};

export type CandidateSession = {
  id: string;
  interview_id: string;
  candidate_id: string;
  status: "invited" | "started" | "submitted" | "reviewed";
  started_at: string | null;
  submitted_at: string | null;
  reviewed_at: string | null;
  latest_code: string | null;
  notes: string | null;
  last_autosaved_at: string | null;
  created_at: string;
  updated_at: string;
  interview: {
    id: string;
    role_title: string;
    seniority: string;
    stack: string[];
    difficulty: string;
    interview_type: string;
    duration_minutes: number;
    allowed_ai_mode: string;
  };
  scenario: {
    id: string;
    title: string;
    business_context: string;
    technical_requirements: string[];
    starter_code: string;
    expected_behavior: string[];
    logs_or_bug_report: string;
    candidate_instructions: string;
  };
  submission: Submission | null;
};

export type TelemetryEventType = "session_started" | "code_edit" | "note_updated" | "test_run" | "submission_created";

export type TelemetryEvent = {
  id: string;
  session_id: string;
  candidate_id: string;
  event_type: TelemetryEventType;
  payload: Record<string, unknown>;
  created_at: string;
};

export type TestCaseResult = {
  name: string;
  status: "passed" | "failed";
  details: string;
};

export type TestRunResult = {
  status: "passed" | "failed";
  output: string;
  cases: TestCaseResult[];
};

export type Submission = {
  id: string;
  session_id: string;
  candidate_id: string;
  code: string;
  notes: string;
  test_output: string | null;
  submitted_at: string;
  created_at: string;
  updated_at: string;
};
