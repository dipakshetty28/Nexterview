"""executable scenario metadata

Revision ID: 0012_exec_scenarios
Revises: 0011_github_starter_branches
Create Date: 2026-05-31
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0012_exec_scenarios"
down_revision = "0011_github_starter_branches"
branch_labels = None
depends_on = None


def upgrade() -> None:
    empty_json_array = sa.text("'[]'::jsonb")
    op.add_column("scenarios", sa.Column("role_title", sa.String(length=140), nullable=False, server_default=""))
    op.add_column("scenarios", sa.Column("seniority", sa.String(length=80), nullable=False, server_default=""))
    op.add_column("scenarios", sa.Column("interview_type", sa.String(length=80), nullable=False, server_default=""))
    op.add_column("scenarios", sa.Column("difficulty", sa.String(length=40), nullable=False, server_default=""))
    op.add_column("scenarios", sa.Column("stack", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=empty_json_array))
    op.add_column("scenarios", sa.Column("language", sa.String(length=80), nullable=False, server_default=""))
    op.add_column("scenarios", sa.Column("framework", sa.String(length=120), nullable=False, server_default=""))
    op.add_column("scenarios", sa.Column("ai_mode", sa.String(length=80), nullable=False, server_default=""))
    op.add_column("scenarios", sa.Column("visible_requirements", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=empty_json_array))
    op.add_column("scenarios", sa.Column("starter_files_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=empty_json_array))
    op.add_column("scenarios", sa.Column("test_files_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=empty_json_array))
    op.add_column("scenarios", sa.Column("expected_solution_files_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=empty_json_array))
    op.add_column("scenarios", sa.Column("bug_description_internal", sa.Text(), nullable=False, server_default=""))
    op.add_column("scenarios", sa.Column("validation_command", sa.String(length=500), nullable=False, server_default=""))
    op.add_column("scenarios", sa.Column("constraints", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=empty_json_array))
    op.add_column("scenarios", sa.Column("expected_solution_summary", sa.Text(), nullable=False, server_default=""))
    op.add_column("scenarios", sa.Column("scenario_fit", sa.Text(), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("scenarios", "scenario_fit")
    op.drop_column("scenarios", "expected_solution_summary")
    op.drop_column("scenarios", "constraints")
    op.drop_column("scenarios", "validation_command")
    op.drop_column("scenarios", "bug_description_internal")
    op.drop_column("scenarios", "expected_solution_files_json")
    op.drop_column("scenarios", "test_files_json")
    op.drop_column("scenarios", "starter_files_json")
    op.drop_column("scenarios", "visible_requirements")
    op.drop_column("scenarios", "ai_mode")
    op.drop_column("scenarios", "framework")
    op.drop_column("scenarios", "language")
    op.drop_column("scenarios", "stack")
    op.drop_column("scenarios", "difficulty")
    op.drop_column("scenarios", "interview_type")
    op.drop_column("scenarios", "seniority")
    op.drop_column("scenarios", "role_title")
