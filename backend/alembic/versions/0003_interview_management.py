"""interviewer interview management

Revision ID: 0003_interview_management
Revises: 0002_auth_rbac
Create Date: 2026-05-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_interview_management"
down_revision = "0002_auth_rbac"
branch_labels = None
depends_on = None


def _create_enum(name: str, *values: str) -> postgresql.ENUM:
    enum = postgresql.ENUM(*values, name=name)
    enum.create(op.get_bind(), checkfirst=True)
    return postgresql.ENUM(*values, name=name, create_type=False)


def upgrade() -> None:
    interview_seniority = _create_enum("interview_seniority", "JUNIOR", "MID", "SENIOR", "STAFF")
    interview_type = _create_enum(
        "interview_type",
        "FULL_STACK_FEATURE",
        "BACKEND_DEBUGGING",
        "API_DESIGN",
        "FRONTEND_BUG_FIX",
        "SYSTEM_DESIGN",
        "AI_ENGINEERING",
        "REFACTORING",
        "SECURITY_REVIEW",
    )
    interview_difficulty = _create_enum("interview_difficulty", "EASY", "MEDIUM", "HARD")
    interview_ai_mode = _create_enum(
        "interview_ai_mode",
        "HINT",
        "PAIR_PROGRAMMER",
        "SENIOR_ENGINEER",
        "DEBUGGING_ASSISTANT",
    )
    interview_status = _create_enum("interview_status", "DRAFT", "ACTIVE", "ARCHIVED")
    interview_session_status = _create_enum(
        "interview_session_status",
        "INVITED",
        "IN_PROGRESS",
        "COMPLETED",
        "CANCELLED",
    )

    op.create_table(
        "interviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("role_title", sa.String(length=140), nullable=False),
        sa.Column("seniority", interview_seniority, nullable=False),
        sa.Column("stack", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("interview_type", interview_type, nullable=False),
        sa.Column("difficulty", interview_difficulty, nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("ai_mode", interview_ai_mode, nullable=False),
        sa.Column("status", interview_status, nullable=False, server_default=sa.text("'DRAFT'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_interviews_created_by_user_id"), "interviews", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_interviews_organization_id"), "interviews", ["organization_id"], unique=False)

    op.create_table(
        "scenarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("interview_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("business_context", sa.Text(), nullable=False),
        sa.Column("candidate_instructions", sa.Text(), nullable=False),
        sa.Column("technical_requirements", sa.Text(), nullable=False),
        sa.Column("evaluation_rubric", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["interview_id"], ["interviews.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scenarios_created_by_user_id"), "scenarios", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_scenarios_interview_id"), "scenarios", ["interview_id"], unique=False)

    op.create_table(
        "interview_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("interview_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", interview_session_status, nullable=False, server_default=sa.text("'INVITED'")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["candidate_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["interview_id"], ["interviews.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_interview_sessions_candidate_user_id"), "interview_sessions", ["candidate_user_id"], unique=False)
    op.create_index(op.f("ix_interview_sessions_interview_id"), "interview_sessions", ["interview_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_interview_sessions_interview_id"), table_name="interview_sessions")
    op.drop_index(op.f("ix_interview_sessions_candidate_user_id"), table_name="interview_sessions")
    op.drop_table("interview_sessions")
    op.drop_index(op.f("ix_scenarios_interview_id"), table_name="scenarios")
    op.drop_index(op.f("ix_scenarios_created_by_user_id"), table_name="scenarios")
    op.drop_table("scenarios")
    op.drop_index(op.f("ix_interviews_organization_id"), table_name="interviews")
    op.drop_index(op.f("ix_interviews_created_by_user_id"), table_name="interviews")
    op.drop_table("interviews")

    for enum_name in (
        "interview_session_status",
        "interview_status",
        "interview_ai_mode",
        "interview_difficulty",
        "interview_type",
        "interview_seniority",
    ):
        postgresql.ENUM(name=enum_name).drop(op.get_bind(), checkfirst=True)
