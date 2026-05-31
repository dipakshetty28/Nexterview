"""github starter branches

Revision ID: 0011_github_starter_branches
Revises: 0010_submission_scores
Create Date: 2026-05-30
"""

from alembic import op
import sqlalchemy as sa

revision = "0011_github_starter_branches"
down_revision = "0010_submission_scores"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scenario_projects", sa.Column("starter_branch_name", sa.String(length=255), nullable=True))
    op.add_column("scenario_projects", sa.Column("starter_commit_sha", sa.String(length=80), nullable=True))
    op.add_column("scenario_projects", sa.Column("starter_repository_url", sa.String(length=500), nullable=True))
    op.add_column("scenario_projects", sa.Column("starter_push_status", sa.String(length=40), nullable=True))
    op.add_column("scenario_projects", sa.Column("starter_push_error", sa.Text(), nullable=True))
    op.add_column("submissions", sa.Column("base_branch_name", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("submissions", "base_branch_name")
    op.drop_column("scenario_projects", "starter_push_error")
    op.drop_column("scenario_projects", "starter_push_status")
    op.drop_column("scenario_projects", "starter_repository_url")
    op.drop_column("scenario_projects", "starter_commit_sha")
    op.drop_column("scenario_projects", "starter_branch_name")
