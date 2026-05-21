from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.interview import InterviewSessionStatus


class InviteCreateRequest(BaseModel):
    candidate_email: EmailStr
    expires_in_days: int = Field(default=14, ge=1, le=60)


class InviteTokenRead(BaseModel):
    id: UUID
    interview_id: UUID
    session_id: UUID
    candidate_email: EmailStr
    invite_url: str
    expires_at: datetime
    used_at: datetime | None


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


class PublicInviteRead(BaseModel):
    interview: InviteInterviewRead
    candidate_email: EmailStr
    expires_at: datetime
    status: InterviewSessionStatus


class CandidateScenarioRead(BaseModel):
    id: UUID
    title: str
    business_context: str
    technical_requirements: list[str]
    starter_code: str
    expected_behavior: list[str]
    logs_or_bug_report: str
    candidate_instructions: str

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


class InterviewSessionRead(BaseModel):
    id: UUID
    interview_id: UUID
    candidate_id: UUID
    status: InterviewSessionStatus
    started_at: datetime | None
    submitted_at: datetime | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    interview: CandidateSessionInterviewRead
    scenario: CandidateScenarioRead

    model_config = ConfigDict(from_attributes=True)
