"""multi file interview projects

Revision ID: 0007_multi_file_projects
Revises: 0006_candidate_ai_messages
Create Date: 2026-05-21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007_multi_file_projects"
down_revision = "0006_candidate_ai_messages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scenarios", sa.Column("bug_description", sa.Text(), server_default="", nullable=False))
    op.add_column("scenarios", sa.Column("feature_request", sa.Text(), server_default="", nullable=False))
    op.add_column("scenarios", sa.Column("validation_instructions", sa.Text(), server_default="", nullable=False))
    op.add_column("scenarios", sa.Column("candidate_task_summary", sa.Text(), server_default="", nullable=False))
    op.add_column(
        "scenarios",
        sa.Column(
            "hidden_rubric",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )

    op.create_table(
        "scenario_projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scenario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "stack",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("project_name", sa.String(length=140), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("run_command", sa.String(length=500), nullable=True),
        sa.Column("test_command", sa.String(length=500), nullable=True),
        sa.Column("install_command", sa.String(length=500), nullable=True),
        sa.Column("entrypoint", sa.String(length=500), nullable=True),
        sa.Column("package_manager", sa.String(length=80), nullable=True),
        sa.Column("framework", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scenario_id", name="uq_scenario_projects_scenario_id"),
    )
    op.create_index(op.f("ix_scenario_projects_scenario_id"), "scenario_projects", ["scenario_id"], unique=False)

    op.create_table(
        "project_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("path", sa.String(length=500), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=80), nullable=False),
        sa.Column("file_type", sa.String(length=40), nullable=False),
        sa.Column("is_editable", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_hidden", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["scenario_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "path", name="uq_project_files_project_path"),
    )
    op.create_index(op.f("ix_project_files_project_id"), "project_files", ["project_id"], unique=False)

    op.create_table(
        "session_file_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("path", sa.String(length=500), nullable=False),
        sa.Column("original_content", sa.Text(), nullable=False),
        sa.Column("current_content", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_file_id"], ["project_files.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["interview_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id",
            "project_file_id",
            name="uq_session_file_snapshots_session_project_file",
        ),
        sa.UniqueConstraint("session_id", "path", name="uq_session_file_snapshots_session_path"),
    )
    op.create_index(
        op.f("ix_session_file_snapshots_project_file_id"),
        "session_file_snapshots",
        ["project_file_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_session_file_snapshots_session_id"),
        "session_file_snapshots",
        ["session_id"],
        unique=False,
    )

    op.add_column(
        "submissions",
        sa.Column(
            "submitted_files",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column("submissions", sa.Column("branch_name", sa.String(length=255), nullable=True))
    op.add_column("submissions", sa.Column("commit_sha", sa.String(length=80), nullable=True))
    op.add_column("submissions", sa.Column("repository_url", sa.String(length=500), nullable=True))
    op.add_column("submissions", sa.Column("pull_request_url", sa.String(length=500), nullable=True))
    op.add_column("submissions", sa.Column("push_status", sa.String(length=40), nullable=True))
    op.add_column("submissions", sa.Column("push_error", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("submissions", "push_error")
    op.drop_column("submissions", "push_status")
    op.drop_column("submissions", "pull_request_url")
    op.drop_column("submissions", "repository_url")
    op.drop_column("submissions", "commit_sha")
    op.drop_column("submissions", "branch_name")
    op.drop_column("submissions", "submitted_files")
    op.drop_index(op.f("ix_session_file_snapshots_session_id"), table_name="session_file_snapshots")
    op.drop_index(op.f("ix_session_file_snapshots_project_file_id"), table_name="session_file_snapshots")
    op.drop_table("session_file_snapshots")
    op.drop_index(op.f("ix_project_files_project_id"), table_name="project_files")
    op.drop_table("project_files")
    op.drop_index(op.f("ix_scenario_projects_scenario_id"), table_name="scenario_projects")
    op.drop_table("scenario_projects")
    op.drop_column("scenarios", "hidden_rubric")
    op.drop_column("scenarios", "candidate_task_summary")
    op.drop_column("scenarios", "validation_instructions")
    op.drop_column("scenarios", "feature_request")
    op.drop_column("scenarios", "bug_description")
