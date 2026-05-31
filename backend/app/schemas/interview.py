from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.scenario import ScenarioRead


DEFAULT_EVALUATION_CRITERIA = [
    "Correctness and edge-case handling",
    "Debugging process and verification discipline",
    "Code quality, maintainability, and error handling",
    "AI collaboration quality and ability to validate suggestions",
]


class InterviewCreateRequest(BaseModel):
    role_title: str = Field(min_length=2, max_length=140)
    seniority: str = Field(min_length=2, max_length=80)
    stack: list[str] = Field(min_length=1, max_length=12)
    difficulty: str = Field(min_length=2, max_length=40)
    interview_type: str = Field(min_length=2, max_length=80)
    duration_minutes: int = Field(ge=30, le=240)
    allowed_ai_mode: str = Field(min_length=2, max_length=80)
    evaluation_criteria: list[str] = Field(default_factory=lambda: list(DEFAULT_EVALUATION_CRITERIA), max_length=12)

    @field_validator("role_title", "seniority", "difficulty", "interview_type", "allowed_ai_mode")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("stack", "evaluation_criteria")
    @classmethod
    def strip_list_items(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if not cleaned:
            raise ValueError("At least one non-empty item is required.")
        return cleaned


class InterviewRead(BaseModel):
    id: UUID
    organization_id: UUID
    created_by_id: UUID | None
    role_title: str
    seniority: str
    stack: list[str]
    difficulty: str
    interview_type: str
    duration_minutes: int
    allowed_ai_mode: str
    evaluation_criteria: list[str]
    status: str
    created_at: datetime
    updated_at: datetime
    scenario: ScenarioRead | None = None

    model_config = ConfigDict(from_attributes=True)


class InterviewSubmissionResultRead(BaseModel):
    session_id: UUID
    candidate_id: UUID
    candidate_email: str
    candidate_name: str
    status: str
    submitted_at: datetime | None
    submission_id: UUID | None
    branch_name: str | None
    base_branch_name: str | None
    commit_sha: str | None
    repository_url: str | None
    pull_request_url: str | None
    push_status: str | None
    push_error: str | None
    test_output: str | None
    notes: str | None
