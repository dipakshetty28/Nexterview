from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User


class Seniority(str, enum.Enum):
    JUNIOR = "JUNIOR"
    MID = "MID"
    SENIOR = "SENIOR"
    STAFF = "STAFF"


class InterviewType(str, enum.Enum):
    FULL_STACK_FEATURE = "FULL_STACK_FEATURE"
    BACKEND_DEBUGGING = "BACKEND_DEBUGGING"
    API_DESIGN = "API_DESIGN"
    FRONTEND_BUG_FIX = "FRONTEND_BUG_FIX"
    SYSTEM_DESIGN = "SYSTEM_DESIGN"
    AI_ENGINEERING = "AI_ENGINEERING"
    REFACTORING = "REFACTORING"
    SECURITY_REVIEW = "SECURITY_REVIEW"


class Difficulty(str, enum.Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class AIMode(str, enum.Enum):
    HINT = "HINT"
    PAIR_PROGRAMMER = "PAIR_PROGRAMMER"
    SENIOR_ENGINEER = "SENIOR_ENGINEER"
    DEBUGGING_ASSISTANT = "DEBUGGING_ASSISTANT"


class InterviewStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class InterviewSessionStatus(str, enum.Enum):
    INVITED = "INVITED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Interview(TimestampMixin, Base):
    __tablename__ = "interviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    role_title: Mapped[str] = mapped_column(String(140), nullable=False)
    seniority: Mapped[Seniority] = mapped_column(Enum(Seniority, name="interview_seniority"), nullable=False)
    stack: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    interview_type: Mapped[InterviewType] = mapped_column(Enum(InterviewType, name="interview_type"), nullable=False)
    difficulty: Mapped[Difficulty] = mapped_column(Enum(Difficulty, name="interview_difficulty"), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    ai_mode: Mapped[AIMode] = mapped_column(Enum(AIMode, name="interview_ai_mode"), nullable=False)
    status: Mapped[InterviewStatus] = mapped_column(
        Enum(InterviewStatus, name="interview_status"),
        nullable=False,
        default=InterviewStatus.DRAFT,
    )

    organization: Mapped[Organization] = relationship("Organization", back_populates="interviews")
    created_by: Mapped[User] = relationship(
        "User",
        back_populates="created_interviews",
        foreign_keys=[created_by_user_id],
    )
    scenarios: Mapped[list[Scenario]] = relationship(
        "Scenario",
        back_populates="interview",
        cascade="all, delete-orphan",
        order_by="Scenario.created_at",
    )
    sessions: Mapped[list[InterviewSession]] = relationship(
        "InterviewSession",
        back_populates="interview",
        cascade="all, delete-orphan",
    )


class Scenario(TimestampMixin, Base):
    __tablename__ = "scenarios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interview_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    business_context: Mapped[str] = mapped_column(Text, nullable=False)
    candidate_instructions: Mapped[str] = mapped_column(Text, nullable=False)
    technical_requirements: Mapped[str] = mapped_column(Text, nullable=False)
    evaluation_rubric: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    interview: Mapped[Interview] = relationship("Interview", back_populates="scenarios")
    created_by: Mapped[User] = relationship(
        "User",
        back_populates="created_scenarios",
        foreign_keys=[created_by_user_id],
    )


class InterviewSession(TimestampMixin, Base):
    __tablename__ = "interview_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interview_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[InterviewSessionStatus] = mapped_column(
        Enum(InterviewSessionStatus, name="interview_session_status"),
        nullable=False,
        default=InterviewSessionStatus.INVITED,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    interview: Mapped[Interview] = relationship("Interview", back_populates="sessions")
    candidate: Mapped[User | None] = relationship(
        "User",
        back_populates="interview_sessions",
        foreign_keys=[candidate_user_id],
    )
