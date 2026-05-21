"""interviews and generated scenarios

Revision ID: 0003_interviews_and_scenarios
Revises: 0002_auth_rbac
Create Date: 2026-05-21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_interviews_and_scenarios"
down_revision = "0002_auth_rbac"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "interviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("role_title", sa.String(length=140), nullable=False),
        sa.Column("seniority", sa.String(length=80), nullable=False),
        sa.Column("stack", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("difficulty", sa.String(length=40), nullable=False),
        sa.Column("interview_type", sa.String(length=80), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("allowed_ai_mode", sa.String(length=80), nullable=False),
        sa.Column("evaluation_criteria", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_interviews_created_by_id"), "interviews", ["created_by_id"], unique=False)
    op.create_index(op.f("ix_interviews_organization_id"), "interviews", ["organization_id"], unique=False)

    op.create_table(
        "scenarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("interview_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("business_context", sa.Text(), nullable=False),
        sa.Column("technical_requirements", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("starter_code", sa.Text(), nullable=False),
        sa.Column("expected_behavior", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("logs_or_bug_report", sa.Text(), nullable=False),
        sa.Column("hidden_evaluation_points", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("candidate_instructions", sa.Text(), nullable=False),
        sa.Column("interviewer_rubric", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("generation_source", sa.String(length=40), nullable=False),
        sa.Column("ai_model", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["interview_id"], ["interviews.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("interview_id", name="uq_scenarios_interview_id"),
    )
    op.create_index(op.f("ix_scenarios_interview_id"), "scenarios", ["interview_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_scenarios_interview_id"), table_name="scenarios")
    op.drop_table("scenarios")
    op.drop_index(op.f("ix_interviews_organization_id"), table_name="interviews")
    op.drop_index(op.f("ix_interviews_created_by_id"), table_name="interviews")
    op.drop_table("interviews")
