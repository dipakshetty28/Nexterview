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
