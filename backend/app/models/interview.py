from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class InterviewSessionStatus(str, enum.Enum):
    INVITED = "invited"
    STARTED = "started"
    SUBMITTED = "submitted"
    READY_FOR_REVIEW = "ready_for_review"
    REVIEW_IN_PROGRESS = "review_in_progress"
    REVIEWED = "reviewed"
    REVIEW_FAILED = "review_failed"


class TelemetryEventType(str, enum.Enum):
    SESSION_STARTED = "session_started"
    CODE_EDIT = "code_edit"
    FILE_OPENED = "file_opened"
    FILE_EDITED = "file_edited"
    FILE_SAVED = "file_saved"
    NOTE_UPDATED = "note_updated"
    TEST_RUN_STARTED = "test_run_started"
    TEST_RUN = "test_run"
    TEST_RUN_COMPLETED = "test_run_completed"
    TEST_RUN_FAILED = "test_run_failed"
    FINAL_TESTS_PASSED = "final_tests_passed"
    FINAL_TESTS_FAILED = "final_tests_failed"
    AI_PROMPT_SENT = "ai_prompt_sent"
    SUBMISSION_CREATED = "submission_created"


class AIMessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"


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
    role_title: Mapped[str] = mapped_column(String(140), nullable=False, default="")
    seniority: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    interview_type: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    difficulty: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    stack: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    language: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    framework: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    ai_mode: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    business_context: Mapped[str] = mapped_column(Text, nullable=False)
    technical_requirements: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    visible_requirements: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    starter_code: Mapped[str] = mapped_column(Text, nullable=False)
    starter_files_json: Mapped[list[dict[str, str]]] = mapped_column(JSONB, nullable=False, default=list)
    test_files_json: Mapped[list[dict[str, str]]] = mapped_column(JSONB, nullable=False, default=list)
    expected_solution_files_json: Mapped[list[dict[str, str]]] = mapped_column(JSONB, nullable=False, default=list)
    expected_behavior: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    logs_or_bug_report: Mapped[str] = mapped_column(Text, nullable=False)
    bug_description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    bug_description_internal: Mapped[str] = mapped_column(Text, nullable=False, default="")
    feature_request: Mapped[str] = mapped_column(Text, nullable=False, default="")
    validation_instructions: Mapped[str] = mapped_column(Text, nullable=False, default="")
    validation_command: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    constraints: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    candidate_task_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    expected_solution_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    scenario_fit: Mapped[str] = mapped_column(Text, nullable=False, default="")
    hidden_evaluation_points: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    hidden_rubric: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    candidate_instructions: Mapped[str] = mapped_column(Text, nullable=False)
    interviewer_rubric: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    generation_source: Mapped[str] = mapped_column(String(40), nullable=False)
    ai_model: Mapped[str | None] = mapped_column(String(120), nullable=True)

    interview: Mapped[Interview] = relationship("Interview", back_populates="scenario")
    project: Mapped[ScenarioProject | None] = relationship(
        "ScenarioProject",
        back_populates="scenario",
        cascade="all, delete-orphan",
        uselist=False,
    )


class ScenarioProject(TimestampMixin, Base):
    __tablename__ = "scenario_projects"
    __table_args__ = (UniqueConstraint("scenario_id", name="uq_scenario_projects_scenario_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scenarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stack: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    project_name: Mapped[str] = mapped_column(String(140), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    run_command: Mapped[str | None] = mapped_column(String(500), nullable=True)
    test_command: Mapped[str | None] = mapped_column(String(500), nullable=True)
    install_command: Mapped[str | None] = mapped_column(String(500), nullable=True)
    entrypoint: Mapped[str | None] = mapped_column(String(500), nullable=True)
    package_manager: Mapped[str | None] = mapped_column(String(80), nullable=True)
    framework: Mapped[str | None] = mapped_column(String(120), nullable=True)
    starter_branch_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    starter_commit_sha: Mapped[str | None] = mapped_column(String(80), nullable=True)
    starter_repository_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    starter_push_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    starter_push_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    scenario: Mapped[Scenario] = relationship("Scenario", back_populates="project")
    files: Mapped[list[ProjectFile]] = relationship(
        "ProjectFile",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ProjectFile.path",
    )


class ProjectFile(TimestampMixin, Base):
    __tablename__ = "project_files"
    __table_args__ = (UniqueConstraint("project_id", "path", name="uq_project_files_project_path"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scenario_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(80), nullable=False)
    file_type: Mapped[str] = mapped_column(String(40), nullable=False)
    is_editable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    project: Mapped[ScenarioProject] = relationship("ScenarioProject", back_populates="files")
    session_snapshots: Mapped[list[SessionFileSnapshot]] = relationship(
        "SessionFileSnapshot",
        back_populates="project_file",
    )


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
    candidate: Mapped["User"] = relationship("User", foreign_keys=[candidate_id])
    invite_tokens: Mapped[list[InviteToken]] = relationship("InviteToken", back_populates="session")
    telemetry_events: Mapped[list[TelemetryEvent]] = relationship(
        "TelemetryEvent",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    test_runs: Mapped[list[TestRun]] = relationship(
        "TestRun",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="TestRun.created_at",
    )
    submission: Mapped[Submission | None] = relationship(
        "Submission",
        back_populates="session",
        cascade="all, delete-orphan",
        uselist=False,
    )
    ai_messages: Mapped[list[AIMessage]] = relationship(
        "AIMessage",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    file_snapshots: Mapped[list[SessionFileSnapshot]] = relationship(
        "SessionFileSnapshot",
        back_populates="session",
        cascade="all, delete-orphan",
    )


class SessionFileSnapshot(TimestampMixin, Base):
    __tablename__ = "session_file_snapshots"
    __table_args__ = (
        UniqueConstraint("session_id", "project_file_id", name="uq_session_file_snapshots_session_project_file"),
        UniqueConstraint("session_id", "path", name="uq_session_file_snapshots_session_path"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_files.id"),
        nullable=False,
        index=True,
    )
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    original_content: Mapped[str] = mapped_column(Text, nullable=False)
    current_content: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(80), nullable=False)

    session: Mapped[InterviewSession] = relationship("InterviewSession", back_populates="file_snapshots")
    project_file: Mapped[ProjectFile] = relationship("ProjectFile", back_populates="session_snapshots")


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
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    token: Mapped[str | None] = mapped_column(String(160), nullable=True, unique=True, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    candidate_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    candidate_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    regenerated_from_invite_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invite_tokens.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    interview: Mapped[Interview] = relationship("Interview", back_populates="invite_tokens")
    session: Mapped[InterviewSession | None] = relationship("InterviewSession", back_populates="invite_tokens")


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
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="submitted")
    submitted_files: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False, default=list)
    file_diffs: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False, default=list)
    branch_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    base_branch_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    commit_sha: Mapped[str | None] = mapped_column(String(80), nullable=True)
    repository_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pull_request_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    push_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    push_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    session: Mapped[InterviewSession] = relationship("InterviewSession", back_populates="submission")
    agent_reviews: Mapped[list[AgentReview]] = relationship(
        "AgentReview",
        back_populates="submission",
        cascade="all, delete-orphan",
        order_by="AgentReview.agent_type",
    )
    score: Mapped[Score | None] = relationship(
        "Score",
        back_populates="submission",
        cascade="all, delete-orphan",
        uselist=False,
    )
    test_runs: Mapped[list[TestRun]] = relationship(
        "TestRun",
        back_populates="submission",
        order_by="TestRun.created_at",
    )


class TestRun(Base):
    __tablename__ = "test_runs"
    __test__ = False

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
    submission_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scenarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    command: Mapped[str] = mapped_column(String(500), nullable=False)
    stdout: Mapped[str] = mapped_column(Text, nullable=False, default="")
    stderr: Mapped[str] = mapped_column(Text, nullable=False, default="")
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    passed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    session: Mapped[InterviewSession] = relationship("InterviewSession", back_populates="test_runs")
    submission: Mapped[Submission | None] = relationship("Submission", back_populates="test_runs")
    scenario: Mapped[Scenario] = relationship("Scenario")


class AgentReview(TimestampMixin, Base):
    __tablename__ = "agent_reviews"
    __table_args__ = (UniqueConstraint("submission_id", "agent_type", name="uq_agent_reviews_submission_agent"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_type: Mapped[str] = mapped_column(String(80), nullable=False)
    agent_label: Mapped[str] = mapped_column(String(120), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    strengths: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    weaknesses: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    evidence: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    risk_flags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    recommendation: Mapped[str] = mapped_column(String(120), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    raw_response: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)

    submission: Mapped[Submission] = relationship("Submission", back_populates="agent_reviews")


class Score(TimestampMixin, Base):
    __tablename__ = "scores"
    __table_args__ = (UniqueConstraint("submission_id", name="uq_scores_submission_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    weighted_score: Mapped[float] = mapped_column(Float, nullable=False)
    recommendation: Mapped[str] = mapped_column(String(120), nullable=False)
    score_breakdown: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False, default=list)
    ai_usage_analysis: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    scoring_version: Mapped[str] = mapped_column(String(40), nullable=False, default="v1")

    submission: Mapped[Submission] = relationship("Submission", back_populates="score")


class AIMessage(TimestampMixin, Base):
    __tablename__ = "ai_messages"

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
    role: Mapped[AIMessageRole] = mapped_column(
        Enum(
            AIMessageRole,
            name="ai_message_role",
            values_callable=lambda roles: [role.value for role in roles],
        ),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    code_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_mode: Mapped[str] = mapped_column(String(80), nullable=False)
    ai_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    message_metadata: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)

    session: Mapped[InterviewSession] = relationship("InterviewSession", back_populates="ai_messages")
