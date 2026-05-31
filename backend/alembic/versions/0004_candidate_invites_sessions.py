"""candidate invite tokens and interview sessions

Revision ID: 0004_candidate_invites_sessions
Revises: 0003_interviews_and_scenarios
Create Date: 2026-05-21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_candidate_invites_sessions"
down_revision = "0003_interviews_and_scenarios"
branch_labels = None
depends_on = None


def upgrade() -> None:
    session_status = postgresql.ENUM(
        "invited",
        "started",
        "submitted",
        "reviewed",
        name="interview_session_status",
    )
    existing_session_status = postgresql.ENUM(
        "invited",
        "started",
        "submitted",
        "reviewed",
        name="interview_session_status",
        create_type=False,
    )
    session_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "interview_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("interview_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", existing_session_status, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["interview_id"], ["interviews.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("interview_id", "candidate_id", name="uq_interview_sessions_interview_candidate"),
    )
    op.create_index(op.f("ix_interview_sessions_candidate_id"), "interview_sessions", ["candidate_id"], unique=False)
    op.create_index(op.f("ix_interview_sessions_interview_id"), "interview_sessions", ["interview_id"], unique=False)
    op.create_index(
        op.f("ix_interview_sessions_organization_id"),
        "interview_sessions",
        ["organization_id"],
        unique=False,
    )

    op.create_table(
        "invite_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("interview_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("candidate_email", sa.String(length=320), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["interview_id"], ["interviews.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["interview_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invite_tokens_candidate_id"), "invite_tokens", ["candidate_id"], unique=False)
    op.create_index(op.f("ix_invite_tokens_created_by_id"), "invite_tokens", ["created_by_id"], unique=False)
    op.create_index(op.f("ix_invite_tokens_interview_id"), "invite_tokens", ["interview_id"], unique=False)
    op.create_index(op.f("ix_invite_tokens_organization_id"), "invite_tokens", ["organization_id"], unique=False)
    op.create_index(op.f("ix_invite_tokens_session_id"), "invite_tokens", ["session_id"], unique=False)
    op.create_index(op.f("ix_invite_tokens_token_hash"), "invite_tokens", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_invite_tokens_token_hash"), table_name="invite_tokens")
    op.drop_index(op.f("ix_invite_tokens_session_id"), table_name="invite_tokens")
    op.drop_index(op.f("ix_invite_tokens_organization_id"), table_name="invite_tokens")
    op.drop_index(op.f("ix_invite_tokens_interview_id"), table_name="invite_tokens")
    op.drop_index(op.f("ix_invite_tokens_created_by_id"), table_name="invite_tokens")
    op.drop_index(op.f("ix_invite_tokens_candidate_id"), table_name="invite_tokens")
    op.drop_table("invite_tokens")
    op.drop_index(op.f("ix_interview_sessions_organization_id"), table_name="interview_sessions")
    op.drop_index(op.f("ix_interview_sessions_interview_id"), table_name="interview_sessions")
    op.drop_index(op.f("ix_interview_sessions_candidate_id"), table_name="interview_sessions")
    op.drop_table("interview_sessions")
    session_status = postgresql.ENUM(name="interview_session_status")
    session_status.drop(op.get_bind(), checkfirst=True)
