"""review status workflow

Revision ID: 0014_review_status_workflow
Revises: 0013_test_runs
Create Date: 2026-06-01
"""

from alembic import op

revision = "0014_review_status_workflow"
down_revision = "0013_test_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for value in ("ready_for_review", "review_in_progress", "review_failed"):
        op.execute(f"ALTER TYPE interview_session_status ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be removed safely without rebuilding the type.
    pass
