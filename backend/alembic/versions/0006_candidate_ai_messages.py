"""candidate ai copilot messages

Revision ID: 0006_candidate_ai_messages
Revises: 0005_candidate_room_telemetry
Create Date: 2026-05-21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_candidate_ai_messages"
down_revision = "0005_candidate_room_telemetry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    role = postgresql.ENUM("user", "assistant", name="ai_message_role")
    existing_role = postgresql.ENUM("user", "assistant", name="ai_message_role", create_type=False)
    role.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "ai_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", existing_role, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("code_snapshot", sa.Text(), nullable=True),
        sa.Column("ai_mode", sa.String(length=80), nullable=False),
        sa.Column("ai_model", sa.String(length=120), nullable=True),
        sa.Column("message_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["interview_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_messages_candidate_id"), "ai_messages", ["candidate_id"], unique=False)
    op.create_index(op.f("ix_ai_messages_organization_id"), "ai_messages", ["organization_id"], unique=False)
    op.create_index(op.f("ix_ai_messages_role"), "ai_messages", ["role"], unique=False)
    op.create_index(op.f("ix_ai_messages_session_id"), "ai_messages", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ai_messages_session_id"), table_name="ai_messages")
    op.drop_index(op.f("ix_ai_messages_role"), table_name="ai_messages")
    op.drop_index(op.f("ix_ai_messages_organization_id"), table_name="ai_messages")
    op.drop_index(op.f("ix_ai_messages_candidate_id"), table_name="ai_messages")
    op.drop_table("ai_messages")
    role = postgresql.ENUM(name="ai_message_role")
    role.drop(op.get_bind(), checkfirst=True)
