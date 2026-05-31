"""repo submission reviews

Revision ID: 0009_repo_submission_reviews
Revises: 0008_candidate_workspace
Create Date: 2026-05-29
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009_repo_submission_reviews"
down_revision = "0008_candidate_workspace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "submissions",
        sa.Column(
            "file_diffs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.create_table(
        "agent_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_type", sa.String(length=80), nullable=False),
        sa.Column("agent_label", sa.String(length=120), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("strengths", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("weaknesses", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("risk_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("recommendation", sa.String(length=120), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("raw_response", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["interview_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("submission_id", "agent_type", name="uq_agent_reviews_submission_agent"),
    )
    op.create_index(op.f("ix_agent_reviews_organization_id"), "agent_reviews", ["organization_id"], unique=False)
    op.create_index(op.f("ix_agent_reviews_session_id"), "agent_reviews", ["session_id"], unique=False)
    op.create_index(op.f("ix_agent_reviews_submission_id"), "agent_reviews", ["submission_id"], unique=False)
    op.alter_column("submissions", "file_diffs", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_agent_reviews_submission_id"), table_name="agent_reviews")
    op.drop_index(op.f("ix_agent_reviews_session_id"), table_name="agent_reviews")
    op.drop_index(op.f("ix_agent_reviews_organization_id"), table_name="agent_reviews")
    op.drop_table("agent_reviews")
    op.drop_column("submissions", "file_diffs")
