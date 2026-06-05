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

export type ScenarioFilePayload = {
  path: string;
  language: string;
  content: string;
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

export type CandidateScenarioProject = {
  project_name: string;
  stack: string[];
  description?: string;
  framework: string | null;
  package_manager: string | null;
  install_command: string | null;
  run_command: string | null;
  test_command: string | null;
  entrypoint: string | null;
  files: ProjectFile[];
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
  role_title: string;
  seniority: string;
  interview_type: string;
  difficulty: string;
  stack: string[];
  language: string;
  framework: string;
  ai_mode: string;
  business_context: string;
  technical_requirements: string[];
  visible_requirements: string[];
  starter_code: string;
  starter_files_json: ScenarioFilePayload[];
  test_files_json: ScenarioFilePayload[];
  expected_solution_files_json: ScenarioFilePayload[];
  expected_behavior: string[];
  logs_or_bug_report: string;
  bug_description: string;
  bug_description_internal: string;
  feature_request: string;
  validation_instructions: string;
  validation_command: string;
  constraints: string[];
  candidate_task_summary: string;
  expected_solution_summary: string;
  scenario_fit: string;
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
  status: "invited" | "started" | "submitted" | "ready_for_review" | "review_in_progress" | "reviewed" | "review_failed";
  invite_status: "active" | "used" | "expired" | "revoked" | null;
  invite_expires_at: string | null;
  invite_used_at: string | null;
  started_at: string | null;
  submitted_at: string | null;
  reviewed_at: string | null;
  submission_id: string | null;
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
  expected: string[];
  observed: string[];
  follow_up_questions: string[];
  confidence: number | null;
  review_source: string | null;
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
  status: "invited" | "started" | "submitted" | "ready_for_review" | "review_in_progress" | "reviewed" | "review_failed";
  submitted_at: string | null;
  reviewed_at: string | null;
  weighted_score: number | null;
  recommendation: string | null;
  risk_flags: string[];
  test_attempt_count: number;
  first_test_status: string | null;
  final_test_status: string | null;
  final_test_summary: string | null;
};

export type TestRunSummary = {
  id: string;
  status: "passed" | "failed" | "error" | "timeout";
  command: string;
  duration_ms: number;
  passed_count: number;
  failed_count: number;
  total_count: number;
  failure_summary: string;
  created_at: string;
};

export type SubmissionReviewSummary = {
  submission_id: string;
  session_id: string;
  candidate_id: string;
  submitted_at: string;
  status: "invited" | "started" | "submitted" | "ready_for_review" | "review_in_progress" | "reviewed" | "review_failed";
  changed_files: string[];
  file_diffs: FileDiff[];
  agent_reviews: AgentReview[];
  score_breakdown: ScoreBreakdownItem[];
  weighted_score: number | null;
  recommendation: string | null;
  ai_usage_analysis: AIUsageAnalysis;
  test_output: string | null;
  test_runs: TestRunSummary[];
  notes: string;
  review_source: string | null;
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
  expected_behavior: string[];
  expected_solution_summary: string;
  hidden_evaluation_points: string[];
  interviewer_rubric: string[];
  candidate_observed: string[];
  candidate_missed: string[];
  suggested_follow_up_questions: string[];
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
  session_id: string | null;
  candidate_id: string | null;
  candidate_email: string | null;
  candidate_name: string | null;
  invite_url: string | null;
  status: "active" | "used" | "expired" | "revoked";
  expires_at: string;
  created_at: string;
  used_at: string | null;
  revoked_at: string | null;
  regenerated_from_invite_id: string | null;
  created_by_user_id: string | null;
  session_status: string | null;
};

export type InviteCreateResponse = InviteTokenResponse & {
  invites: InviteTokenResponse[];
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
  candidate_email: string | null;
  candidate_name: string | null;
  expires_at: string;
  status: "active" | "used" | "expired" | "revoked";
};

export type CandidateSession = {
  id: string;
  interview_id: string;
  candidate_id: string;
  status: "invited" | "started" | "submitted" | "ready_for_review" | "review_in_progress" | "reviewed" | "review_failed";
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
    visible_requirements: string[];
    starter_files_json: ScenarioFilePayload[];
    test_files_json: ScenarioFilePayload[];
    starter_code: string;
    expected_behavior: string[];
    logs_or_bug_report: string;
    bug_description: string;
    feature_request: string;
    validation_instructions: string;
    validation_command: string;
    constraints: string[];
    candidate_task_summary: string;
    candidate_instructions: string;
    ai_mode: string;
    language: string;
    framework: string;
    project: CandidateScenarioProject | null;
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
  ai_mode: string;
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
  | "test_run_started"
  | "test_run"
  | "test_run_completed"
  | "test_run_failed"
  | "final_tests_passed"
  | "final_tests_failed"
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
  status: "passed" | "failed" | "error" | "timeout";
  command: string;
  stdout: string;
  stderr: string;
  duration_ms: number;
  passed_count: number;
  failed_count: number;
  total_count: number;
  failure_summary: string;
  created_at: string;
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
  status: "submitted" | "tests_failed" | "ready_for_review" | "review_in_progress" | "reviewed" | "review_failed";
  submitted_files: Array<Record<string, unknown>>;
  file_diffs: Array<Record<string, unknown>>;
  submitted_at: string;
  created_at: string;
  updated_at: string;
};
