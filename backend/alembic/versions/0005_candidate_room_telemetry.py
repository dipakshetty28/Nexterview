"""candidate room telemetry and submissions

Revision ID: 0005_candidate_room_telemetry
Revises: 0004_candidate_invites_sessions
Create Date: 2026-05-21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_candidate_room_telemetry"
down_revision = "0004_candidate_invites_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    event_type = postgresql.ENUM(
        "session_started",
        "code_edit",
        "note_updated",
        "test_run",
        "submission_created",
        name="telemetry_event_type",
    )
    existing_event_type = postgresql.ENUM(
        "session_started",
        "code_edit",
        "note_updated",
        "test_run",
        "submission_created",
        name="telemetry_event_type",
        create_type=False,
    )
    event_type.create(op.get_bind(), checkfirst=True)

    op.add_column("interview_sessions", sa.Column("latest_code", sa.Text(), nullable=True))
    op.add_column("interview_sessions", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("interview_sessions", sa.Column("last_autosaved_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "telemetry_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", existing_event_type, nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["interview_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_telemetry_events_candidate_id"), "telemetry_events", ["candidate_id"], unique=False)
    op.create_index(op.f("ix_telemetry_events_event_type"), "telemetry_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_telemetry_events_organization_id"), "telemetry_events", ["organization_id"], unique=False)
    op.create_index(op.f("ix_telemetry_events_session_id"), "telemetry_events", ["session_id"], unique=False)

    op.create_table(
        "submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("test_output", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["interview_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", name="uq_submissions_session_id"),
    )
    op.create_index(op.f("ix_submissions_candidate_id"), "submissions", ["candidate_id"], unique=False)
    op.create_index(op.f("ix_submissions_organization_id"), "submissions", ["organization_id"], unique=False)
    op.create_index(op.f("ix_submissions_session_id"), "submissions", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_submissions_session_id"), table_name="submissions")
    op.drop_index(op.f("ix_submissions_organization_id"), table_name="submissions")
    op.drop_index(op.f("ix_submissions_candidate_id"), table_name="submissions")
    op.drop_table("submissions")
    op.drop_index(op.f("ix_telemetry_events_session_id"), table_name="telemetry_events")
    op.drop_index(op.f("ix_telemetry_events_organization_id"), table_name="telemetry_events")
    op.drop_index(op.f("ix_telemetry_events_event_type"), table_name="telemetry_events")
    op.drop_index(op.f("ix_telemetry_events_candidate_id"), table_name="telemetry_events")
    op.drop_table("telemetry_events")
    op.drop_column("interview_sessions", "last_autosaved_at")
    op.drop_column("interview_sessions", "notes")
    op.drop_column("interview_sessions", "latest_code")
    event_type = postgresql.ENUM(name="telemetry_event_type")
    event_type.drop(op.get_bind(), checkfirst=True)
