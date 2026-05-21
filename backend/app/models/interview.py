from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


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
