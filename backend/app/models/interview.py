from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class InterviewSessionStatus(str, enum.Enum):
    INVITED = "invited"
    STARTED = "started"
    SUBMITTED = "submitted"
    REVIEWED = "reviewed"


class TelemetryEventType(str, enum.Enum):
    SESSION_STARTED = "session_started"
    CODE_EDIT = "code_edit"
    NOTE_UPDATED = "note_updated"
    TEST_RUN = "test_run"
    SUBMISSION_CREATED = "submission_created"


class Interview(TimestampMixin, Base):
    __tablename__ = "interviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    role_title: Mapped[str] = mapped_column(String(140), nullable=False)
    seniority: Mapped[str] = mapped_column(String(80), nullable=False)
    stack: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    difficulty: Mapped[str] = mapped_column(String(40), nullable=False)
    interview_type: Mapped[str] = mapped_column(String(80), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    allowed_ai_mode: Mapped[str] = mapped_column(String(80), nullable=False)
    evaluation_criteria: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="DRAFT")

    scenario: Mapped[Scenario | None] = relationship(
        "Scenario",
        back_populates="interview",
        cascade="all, delete-orphan",
        uselist=False,
    )
    sessions: Mapped[list[InterviewSession]] = relationship(
        "InterviewSession",
        back_populates="interview",
        cascade="all, delete-orphan",
    )
    invite_tokens: Mapped[list[InviteToken]] = relationship(
        "InviteToken",
        back_populates="interview",
        cascade="all, delete-orphan",
    )


class Scenario(TimestampMixin, Base):
    __tablename__ = "scenarios"
    __table_args__ = (UniqueConstraint("interview_id", name="uq_scenarios_interview_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interview_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    business_context: Mapped[str] = mapped_column(Text, nullable=False)
    technical_requirements: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    starter_code: Mapped[str] = mapped_column(Text, nullable=False)
    expected_behavior: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    logs_or_bug_report: Mapped[str] = mapped_column(Text, nullable=False)
    hidden_evaluation_points: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    candidate_instructions: Mapped[str] = mapped_column(Text, nullable=False)
    interviewer_rubric: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    generation_source: Mapped[str] = mapped_column(String(40), nullable=False)
    ai_model: Mapped[str | None] = mapped_column(String(120), nullable=True)

    interview: Mapped[Interview] = relationship("Interview", back_populates="scenario")


class InterviewSession(TimestampMixin, Base):
    __tablename__ = "interview_sessions"
    __table_args__ = (
        UniqueConstraint("interview_id", "candidate_id", name="uq_interview_sessions_interview_candidate"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    interview_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[InterviewSessionStatus] = mapped_column(
        Enum(
            InterviewSessionStatus,
            name="interview_session_status",
            values_callable=lambda statuses: [status.value for status in statuses],
        ),
        nullable=False,
        default=InterviewSessionStatus.INVITED,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latest_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_autosaved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    interview: Mapped[Interview] = relationship("Interview", back_populates="sessions")
    invite_tokens: Mapped[list[InviteToken]] = relationship("InviteToken", back_populates="session")
    telemetry_events: Mapped[list[TelemetryEvent]] = relationship(
        "TelemetryEvent",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    submission: Mapped[Submission | None] = relationship(
        "Submission",
        back_populates="session",
        cascade="all, delete-orphan",
        uselist=False,
    )


class InviteToken(TimestampMixin, Base):
    __tablename__ = "invite_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    interview_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    candidate_email: Mapped[str] = mapped_column(String(320), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    interview: Mapped[Interview] = relationship("Interview", back_populates="invite_tokens")
    session: Mapped[InterviewSession] = relationship("InterviewSession", back_populates="invite_tokens")


class TelemetryEvent(TimestampMixin, Base):
    __tablename__ = "telemetry_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[TelemetryEventType] = mapped_column(
        Enum(
            TelemetryEventType,
            name="telemetry_event_type",
            values_callable=lambda event_types: [event_type.value for event_type in event_types],
        ),
        nullable=False,
        index=True,
    )
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)

    session: Mapped[InterviewSession] = relationship("InterviewSession", back_populates="telemetry_events")


class Submission(TimestampMixin, Base):
    __tablename__ = "submissions"
    __table_args__ = (UniqueConstraint("session_id", name="uq_submissions_session_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    test_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    session: Mapped[InterviewSession] = relationship("InterviewSession", back_populates="submission")
