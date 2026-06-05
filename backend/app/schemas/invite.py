from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models.interview import AIMessageRole, InterviewSessionStatus, TelemetryEventType
from app.schemas.project import CandidateScenarioProjectRead, SubmittedFileRead


class InviteCreateRequest(BaseModel):
    candidate_email: EmailStr | None = None
    candidate_name: str | None = Field(default=None, max_length=160)
    expires_in_days: int = Field(default=14, ge=1, le=60)
    invite_count: int = Field(default=1, ge=1, le=25)

    @field_validator("candidate_name")
    @classmethod
    def strip_candidate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def validate_bulk_candidate_target(self) -> "InviteCreateRequest":
        if self.candidate_email and self.invite_count != 1:
            raise ValueError("Candidate-specific invites must be generated one at a time.")
        return self


class InviteTokenRead(BaseModel):
    id: UUID
    interview_id: UUID
    session_id: UUID | None
    candidate_id: UUID | None = None
    candidate_email: EmailStr | None
    candidate_name: str | None = None
    invite_url: str | None
    status: str
    expires_at: datetime
    created_at: datetime
    used_at: datetime | None
    revoked_at: datetime | None = None
    regenerated_from_invite_id: UUID | None = None
    created_by_user_id: UUID | None = None
    session_status: str | None = None


class InviteCreateResponse(InviteTokenRead):
    invites: list[InviteTokenRead] = Field(default_factory=list)


class InviteRegenerateRequest(BaseModel):
    expires_in_days: int = Field(default=14, ge=1, le=60)


class InviteInterviewRead(BaseModel):
    id: UUID
    role_title: str
    seniority: str
    stack: list[str]
    difficulty: str
    interview_type: str
    duration_minutes: int
    allowed_ai_mode: str
    scenario_title: str | None = None
    scenario_status: str | None = None
    is_ready: bool = False


class PublicInviteRead(BaseModel):
    interview: InviteInterviewRead
    candidate_email: EmailStr | None
    candidate_name: str | None = None
    expires_at: datetime
    status: str


class CandidateScenarioRead(BaseModel):
    id: UUID
    title: str
    business_context: str
    technical_requirements: list[str]
    visible_requirements: list[str]
    starter_files_json: list[dict[str, str]]
    test_files_json: list[dict[str, str]]
    starter_code: str
    expected_behavior: list[str]
    logs_or_bug_report: str
    bug_description: str
    feature_request: str
    validation_instructions: str
    validation_command: str
    constraints: list[str]
    candidate_task_summary: str
    candidate_instructions: str
    ai_mode: str
    language: str
    framework: str
    project: CandidateScenarioProjectRead | None = None

    model_config = ConfigDict(from_attributes=True)


class CandidateSessionInterviewRead(BaseModel):
    id: UUID
    role_title: str
    seniority: str
    stack: list[str]
    difficulty: str
    interview_type: str
    duration_minutes: int
    allowed_ai_mode: str

    model_config = ConfigDict(from_attributes=True)


class SubmissionRead(BaseModel):
    id: UUID
    session_id: UUID
    candidate_id: UUID
    code: str
    notes: str
    test_output: str | None
    status: str
    submitted_files: list[dict[str, Any]]
    file_diffs: list[dict[str, Any]]
    submitted_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AIMessageRead(BaseModel):
    id: UUID
    session_id: UUID
    candidate_id: UUID
    role: AIMessageRole
    content: str
    ai_mode: str
    message_metadata: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InterviewSessionRead(BaseModel):
    id: UUID
    interview_id: UUID
    candidate_id: UUID
    status: InterviewSessionStatus
    started_at: datetime | None
    submitted_at: datetime | None
    reviewed_at: datetime | None
    latest_code: str | None
    notes: str | None
    last_autosaved_at: datetime | None
    created_at: datetime
    updated_at: datetime
    interview: CandidateSessionInterviewRead
    scenario: CandidateScenarioRead
    submission: SubmissionRead | None
    ai_messages: list[AIMessageRead]

    model_config = ConfigDict(from_attributes=True)


class TelemetryEventCreate(BaseModel):
    event_type: TelemetryEventType
    payload: dict[str, Any] = Field(default_factory=dict)


class TelemetryEventRead(BaseModel):
    id: UUID
    session_id: UUID
    candidate_id: UUID
    event_type: TelemetryEventType
    payload: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TestRunRequest(BaseModel):
    code: str | None = None


class TestCaseResult(BaseModel):
    name: str
    status: str
    details: str


class TestRunResult(BaseModel):
    status: str
    command: str
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = 0
    passed_count: int = 0
    failed_count: int = 0
    total_count: int = 0
    failure_summary: str = ""
    created_at: datetime
    output: str
    cases: list[TestCaseResult]


class SubmissionCreate(BaseModel):
    code: str = Field(default="", max_length=200000)
    notes: str = Field(default="", max_length=10000)
    test_output: str | None = Field(default=None, max_length=20000)
    submitted_files: list[SubmittedFileRead] = Field(default_factory=list, max_length=120)


class AICopilotRequest(BaseModel):
    question: str = Field(min_length=1, max_length=6000)
    code: str = Field(default="", max_length=200000)
    current_file_path: str | None = Field(default=None, max_length=500)
    current_file_content: str | None = Field(default=None, max_length=200000)
    latest_test_output: str | None = Field(default=None, max_length=20000)
    notes: str | None = Field(default=None, max_length=10000)


class CopilotSuggestedFileRead(BaseModel):
    path: str
    reason: str


class CopilotStructuredResponse(BaseModel):
    answer: str
    suggested_files: list[CopilotSuggestedFileRead] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    confidence: str


class AICopilotResponse(BaseModel):
    user_message: AIMessageRead
    assistant_message: AIMessageRead
    response: CopilotStructuredResponse
