"""test run validation records

Revision ID: 0013_test_runs
Revises: 0012_exec_scenarios
Create Date: 2026-05-31
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0013_test_runs"
down_revision = "0012_exec_scenarios"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for value in (
        "test_run_started",
        "test_run_completed",
        "test_run_failed",
        "final_tests_passed",
        "final_tests_failed",
    ):
        op.execute(f"ALTER TYPE telemetry_event_type ADD VALUE IF NOT EXISTS '{value}'")

    op.add_column("submissions", sa.Column("status", sa.String(length=40), nullable=False, server_default="submitted"))
    op.create_table(
        "test_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scenario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("command", sa.String(length=500), nullable=False),
        sa.Column("stdout", sa.Text(), nullable=False, server_default=""),
        sa.Column("stderr", sa.Text(), nullable=False, server_default=""),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("passed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failure_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["interview_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_test_runs_organization_id"), "test_runs", ["organization_id"], unique=False)
    op.create_index(op.f("ix_test_runs_scenario_id"), "test_runs", ["scenario_id"], unique=False)
    op.create_index(op.f("ix_test_runs_session_id"), "test_runs", ["session_id"], unique=False)
    op.create_index(op.f("ix_test_runs_submission_id"), "test_runs", ["submission_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_test_runs_submission_id"), table_name="test_runs")
    op.drop_index(op.f("ix_test_runs_session_id"), table_name="test_runs")
    op.drop_index(op.f("ix_test_runs_scenario_id"), table_name="test_runs")
    op.drop_index(op.f("ix_test_runs_organization_id"), table_name="test_runs")
    op.drop_table("test_runs")
    op.drop_column("submissions", "status")
