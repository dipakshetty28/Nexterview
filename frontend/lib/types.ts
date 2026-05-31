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

export type ProjectFile = {
  id?: string;
  project_id?: string;
  path: string;
  content: string;
  language: string;
  file_type: string;
  is_editable: boolean;
  is_hidden?: boolean;
  created_at?: string;
  updated_at?: string;
};

export type ScenarioProject = {
  id?: string;
  scenario_id?: string;
  project_name: string;
  stack: string[];
  description?: string;
  framework: string | null;
  package_manager: string | null;
  install_command: string | null;
  run_command: string | null;
  test_command: string | null;
  entrypoint: string | null;
  starter_branch_name?: string | null;
  starter_commit_sha?: string | null;
  starter_repository_url?: string | null;
  starter_push_status?: string | null;
  starter_push_error?: string | null;
  files: ProjectFile[];
  created_at?: string;
  updated_at?: string;
};

export type WorkspaceFile = {
  id: string;
  project_file_id: string;
  path: string;
  original_content: string;
  current_content: string;
  language: string;
  file_type: string;
  is_editable: boolean;
  updated_at: string;
};

export type WorkspaceProject = {
  id: string;
  project_name: string;
  stack: string[];
  description: string;
  framework: string | null;
  package_manager: string | null;
  install_command: string | null;
  run_command: string | null;
  test_command: string | null;
  entrypoint: string | null;
};

export type CandidateWorkspace = {
  session_id: string;
  project: WorkspaceProject | null;
  files: WorkspaceFile[];
  last_autosaved_at: string | null;
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
  bug_description: string;
  feature_request: string;
  validation_instructions: string;
  candidate_task_summary: string;
  hidden_evaluation_points: string[];
  hidden_rubric: string[];
  candidate_instructions: string;
  interviewer_rubric: string[];
  generation_source: string;
  ai_model: string | null;
  project: ScenarioProject | null;
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

export type InterviewSubmissionResult = {
  session_id: string;
  candidate_id: string;
  candidate_email: string;
  candidate_name: string;
  status: "invited" | "started" | "submitted" | "reviewed";
  submitted_at: string | null;
  submission_id: string | null;
  branch_name: string | null;
  base_branch_name: string | null;
  commit_sha: string | null;
  repository_url: string | null;
  pull_request_url: string | null;
  push_status: string | null;
  push_error: string | null;
  test_output: string | null;
  notes: string | null;
};

export type FileDiff = {
  path: string;
  status: string;
  language: string;
  file_type: string;
  additions: number;
  deletions: number;
  diff: string;
};

export type AgentReview = {
  id: string;
  submission_id: string;
  session_id: string;
  agent_type: string;
  agent_label: string;
  score: number;
  strengths: string[];
  weaknesses: string[];
  evidence: string[];
  risk_flags: string[];
  recommendation: string;
  explanation: string;
  raw_response: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ScoreBreakdownItem = {
  agent_type: string;
  label: string;
  weight: number;
  score: number | null;
  weighted_score: number | null;
};

export type GitHubReviewLinks = {
  branch_name: string | null;
  base_branch_name: string | null;
  commit_sha: string | null;
  repository_url: string | null;
  pull_request_url: string | null;
  push_status: string | null;
  push_error: string | null;
};

export type AIUsageAnalysis = {
  candidate_prompt_count: number;
  assistant_response_count: number;
  prompts_with_file_context: number;
  test_run_count: number;
  response_confidence_values: string[];
  validated_suggestions: boolean;
  summary: string;
};

export type SubmittedCodeFile = {
  path: string;
  content: string;
  language: string;
  file_type: string | null;
};

export type AITranscriptMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  ai_mode: string;
  ai_model: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type TelemetryTimelineEvent = {
  id: string;
  event_type: TelemetryEventType;
  payload: Record<string, unknown>;
  created_at: string;
};

export type PromptQualitySummary = {
  candidate_prompt_count: number;
  prompts_with_file_context: number;
  vague_prompt_count: number;
  validation_prompt_count: number;
  average_prompt_length: number;
  summary: string;
  strengths: string[];
  risks: string[];
};

export type ResultsDashboardItem = {
  session_id: string;
  submission_id: string | null;
  interview_id: string;
  candidate_id: string;
  candidate_email: string;
  candidate_name: string;
  role_title: string;
  scenario_title: string | null;
  status: "invited" | "started" | "submitted" | "reviewed";
  submitted_at: string | null;
  reviewed_at: string | null;
  weighted_score: number | null;
  recommendation: string | null;
  push_status: string | null;
  pull_request_url: string | null;
  risk_flags: string[];
};

export type SubmissionReviewSummary = {
  submission_id: string;
  session_id: string;
  candidate_id: string;
  submitted_at: string;
  status: "invited" | "started" | "submitted" | "reviewed";
  changed_files: string[];
  file_diffs: FileDiff[];
  github: GitHubReviewLinks;
  agent_reviews: AgentReview[];
  score_breakdown: ScoreBreakdownItem[];
  weighted_score: number | null;
  recommendation: string | null;
  ai_usage_analysis: AIUsageAnalysis;
  test_output: string | null;
  notes: string;
};

export type SessionResult = SubmissionReviewSummary & {
  candidate_email: string;
  candidate_name: string;
  interview_id: string;
  role_title: string;
  scenario_title: string;
  bug_description: string;
  feature_request: string;
  validation_instructions: string;
  submitted_files: SubmittedCodeFile[];
  ai_chat_transcript: AITranscriptMessage[];
  telemetry_timeline: TelemetryTimelineEvent[];
  prompt_quality_summary: PromptQualitySummary;
  risk_flags: string[];
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
    bug_description: string;
    feature_request: string;
    validation_instructions: string;
    candidate_task_summary: string;
    candidate_instructions: string;
    project: ScenarioProject | null;
  };
  submission: Submission | null;
  ai_messages: AIMessage[];
};

export type AIMessage = {
  id: string;
  session_id: string;
  candidate_id: string;
  role: "user" | "assistant";
  content: string;
  code_snapshot: string | null;
  ai_mode: string;
  ai_model: string | null;
  message_metadata: Record<string, unknown>;
  created_at: string;
};

export type CopilotSuggestedFile = {
  path: string;
  reason: string;
};

export type CopilotStructuredResponse = {
  answer: string;
  suggested_files: CopilotSuggestedFile[];
  risk_flags: string[];
  confidence: "low" | "medium" | "high";
};

export type AICopilotResponse = {
  user_message: AIMessage;
  assistant_message: AIMessage;
  response: CopilotStructuredResponse;
};

export type TelemetryEventType =
  | "session_started"
  | "code_edit"
  | "file_opened"
  | "file_edited"
  | "file_saved"
  | "note_updated"
  | "test_run"
  | "ai_prompt_sent"
  | "submission_created";

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
  submitted_files: Array<Record<string, unknown>>;
  file_diffs: Array<Record<string, unknown>>;
  branch_name: string | null;
  base_branch_name: string | null;
  commit_sha: string | null;
  repository_url: string | null;
  pull_request_url: string | null;
  push_status: string | null;
  push_error: string | null;
  submitted_at: string;
  created_at: string;
  updated_at: string;
};
