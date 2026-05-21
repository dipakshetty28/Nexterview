from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.interview import Interview, InterviewSession, Scenario
    from app.models.organization import OrganizationMember


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    INTERVIEWER = "INTERVIEWER"
    CANDIDATE = "CANDIDATE"


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        nullable=False,
        default=UserRole.CANDIDATE,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    memberships: Mapped[list[OrganizationMember]] = relationship(
        "OrganizationMember",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    created_interviews: Mapped[list[Interview]] = relationship(
        "Interview",
        back_populates="created_by",
        foreign_keys="Interview.created_by_user_id",
    )
    created_scenarios: Mapped[list[Scenario]] = relationship(
        "Scenario",
        back_populates="created_by",
        foreign_keys="Scenario.created_by_user_id",
    )
    interview_sessions: Mapped[list[InterviewSession]] = relationship(
        "InterviewSession",
        back_populates="candidate",
        foreign_keys="InterviewSession.candidate_user_id",
    )
