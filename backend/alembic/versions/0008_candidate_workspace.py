"""candidate workspace telemetry

Revision ID: 0008_candidate_workspace
Revises: 0007_multi_file_projects
Create Date: 2026-05-21
"""

from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0008_candidate_workspace"
down_revision = "0007_multi_file_projects"
branch_labels = None
depends_on = None


NEW_EVENT_TYPES = ("file_opened", "file_edited", "file_saved", "ai_prompt_sent")
OLD_EVENT_TYPES = ("session_started", "code_edit", "note_updated", "test_run", "submission_created")


def upgrade() -> None:
    for event_type in NEW_EVENT_TYPES:
        op.execute(f"ALTER TYPE telemetry_event_type ADD VALUE IF NOT EXISTS '{event_type}'")


def downgrade() -> None:
    quoted_values = ", ".join(f"'{event_type}'" for event_type in NEW_EVENT_TYPES)
    op.execute(f"DELETE FROM telemetry_events WHERE event_type::text IN ({quoted_values})")
    op.execute("ALTER TABLE telemetry_events ALTER COLUMN event_type TYPE text USING event_type::text")
    op.execute("DROP TYPE telemetry_event_type")

    old_enum = postgresql.ENUM(*OLD_EVENT_TYPES, name="telemetry_event_type")
    old_enum.create(op.get_bind(), checkfirst=False)
    op.execute(
        "ALTER TABLE telemetry_events "
        "ALTER COLUMN event_type TYPE telemetry_event_type "
        "USING event_type::telemetry_event_type"
    )
