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

export type Seniority = "JUNIOR" | "MID" | "SENIOR" | "STAFF";

export type InterviewType =
  | "FULL_STACK_FEATURE"
  | "BACKEND_DEBUGGING"
  | "API_DESIGN"
  | "FRONTEND_BUG_FIX"
  | "SYSTEM_DESIGN"
  | "AI_ENGINEERING"
  | "REFACTORING"
  | "SECURITY_REVIEW";

export type Difficulty = "EASY" | "MEDIUM" | "HARD";

export type AIMode = "HINT" | "PAIR_PROGRAMMER" | "SENIOR_ENGINEER" | "DEBUGGING_ASSISTANT";

export type InterviewStatus = "DRAFT" | "ACTIVE" | "ARCHIVED";

export type Scenario = {
  id: string;
  title: string;
  business_context: string;
  candidate_instructions: string;
  technical_requirements: string;
  evaluation_rubric: string;
  created_at: string;
  updated_at: string;
};

export type Interview = {
  id: string;
  organization: Organization;
  created_by: {
    id: string;
    email: string;
    full_name: string;
  };
  title: string;
  role_title: string;
  seniority: Seniority;
  stack: string[];
  interview_type: InterviewType;
  difficulty: Difficulty;
  duration_minutes: number;
  ai_mode: AIMode;
  status: InterviewStatus;
  scenarios: Scenario[];
  session_count: number;
  created_at: string;
  updated_at: string;
};

export type InterviewListResponse = {
  interviews: Interview[];
};

export type ScenarioInput = {
  title: string;
  business_context: string;
  candidate_instructions: string;
  technical_requirements: string;
  evaluation_rubric: string;
};

export type InterviewInput = {
  organization_id?: string;
  title: string;
  role_title: string;
  seniority: Seniority;
  stack: string[];
  interview_type: InterviewType;
  difficulty: Difficulty;
  duration_minutes: number;
  ai_mode: AIMode;
  scenario: ScenarioInput;
};
