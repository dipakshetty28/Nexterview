from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.interview import AIMode, Difficulty, InterviewStatus, InterviewType, Seniority
from app.schemas.auth import OrganizationRead


class UserSummary(BaseModel):
    id: UUID
    email: str
    full_name: str

    model_config = ConfigDict(from_attributes=True)


class ScenarioBase(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    business_context: str = Field(min_length=20, max_length=4000)
    candidate_instructions: str = Field(min_length=20, max_length=6000)
    technical_requirements: str = Field(min_length=20, max_length=6000)
    evaluation_rubric: str = Field(min_length=20, max_length=6000)


class ScenarioCreate(ScenarioBase):
    pass


class ScenarioUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=180)
    business_context: str | None = Field(default=None, min_length=20, max_length=4000)
    candidate_instructions: str | None = Field(default=None, min_length=20, max_length=6000)
    technical_requirements: str | None = Field(default=None, min_length=20, max_length=6000)
    evaluation_rubric: str | None = Field(default=None, min_length=20, max_length=6000)


class ScenarioRead(ScenarioBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InterviewBase(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    role_title: str = Field(min_length=2, max_length=140)
    seniority: Seniority
    stack: list[str] = Field(min_length=1, max_length=12)
    interview_type: InterviewType
    difficulty: Difficulty
    duration_minutes: int = Field(ge=15, le=240)
    ai_mode: AIMode

    @field_validator("stack")
    @classmethod
    def normalize_stack(cls, stack: list[str]) -> list[str]:
        normalized = [item.strip() for item in stack if item.strip()]
        if not normalized:
            raise ValueError("At least one stack item is required.")
        if len(set(item.lower() for item in normalized)) != len(normalized):
            raise ValueError("Stack items must be unique.")
        return normalized


class InterviewCreate(InterviewBase):
    organization_id: UUID | None = None
    scenario: ScenarioCreate


class InterviewUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=180)
    role_title: str | None = Field(default=None, min_length=2, max_length=140)
    seniority: Seniority | None = None
    stack: list[str] | None = Field(default=None, min_length=1, max_length=12)
    interview_type: InterviewType | None = None
    difficulty: Difficulty | None = None
    duration_minutes: int | None = Field(default=None, ge=15, le=240)
    ai_mode: AIMode | None = None
    status: InterviewStatus | None = None
    scenario: ScenarioUpdate | None = None

    @field_validator("stack")
    @classmethod
    def normalize_stack(cls, stack: list[str] | None) -> list[str] | None:
        if stack is None:
            return None
        normalized = [item.strip() for item in stack if item.strip()]
        if not normalized:
            raise ValueError("At least one stack item is required.")
        if len(set(item.lower() for item in normalized)) != len(normalized):
            raise ValueError("Stack items must be unique.")
        return normalized


class InterviewRead(InterviewBase):
    id: UUID
    organization: OrganizationRead
    created_by: UserSummary
    status: InterviewStatus
    scenarios: list[ScenarioRead]
    session_count: int
    created_at: datetime
    updated_at: datetime


class InterviewListResponse(BaseModel):
    interviews: list[InterviewRead]
