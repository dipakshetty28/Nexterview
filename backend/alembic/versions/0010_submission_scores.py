"""submission scores

Revision ID: 0010_submission_scores
Revises: 0009_repo_submission_reviews
Create Date: 2026-05-30
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0010_submission_scores"
down_revision = "0009_repo_submission_reviews"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("weighted_score", sa.Float(), nullable=False),
        sa.Column("recommendation", sa.String(length=120), nullable=False),
        sa.Column("score_breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("ai_usage_analysis", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("scoring_version", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["interview_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("submission_id", name="uq_scores_submission_id"),
    )
    op.create_index(op.f("ix_scores_organization_id"), "scores", ["organization_id"], unique=False)
    op.create_index(op.f("ix_scores_session_id"), "scores", ["session_id"], unique=False)
    op.create_index(op.f("ix_scores_submission_id"), "scores", ["submission_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_scores_submission_id"), table_name="scores")
    op.drop_index(op.f("ix_scores_session_id"), table_name="scores")
    op.drop_index(op.f("ix_scores_organization_id"), table_name="scores")
    op.drop_table("scores")
