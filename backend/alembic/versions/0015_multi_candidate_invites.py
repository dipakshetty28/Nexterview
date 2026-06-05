"""multi candidate invite management

Revision ID: 0015_multi_candidate_invites
Revises: 0014_review_status_workflow
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0015_multi_candidate_invites"
down_revision = "0014_review_status_workflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("invite_tokens", sa.Column("token", sa.String(length=160), nullable=True))
    op.add_column("invite_tokens", sa.Column("candidate_name", sa.String(length=160), nullable=True))
    op.add_column("invite_tokens", sa.Column("status", sa.String(length=40), nullable=False, server_default="active"))
    op.add_column(
        "invite_tokens",
        sa.Column("regenerated_from_invite_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(op.f("ix_invite_tokens_token"), "invite_tokens", ["token"], unique=True)
    op.create_index(
        op.f("ix_invite_tokens_regenerated_from_invite_id"),
        "invite_tokens",
        ["regenerated_from_invite_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_invite_tokens_regenerated_from_invite_id",
        "invite_tokens",
        "invite_tokens",
        ["regenerated_from_invite_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.alter_column("invite_tokens", "session_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)
    op.alter_column("invite_tokens", "candidate_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)
    op.alter_column("invite_tokens", "candidate_email", existing_type=sa.String(length=320), nullable=True)


def downgrade() -> None:
    op.alter_column("invite_tokens", "candidate_email", existing_type=sa.String(length=320), nullable=False)
    op.alter_column("invite_tokens", "candidate_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)
    op.alter_column("invite_tokens", "session_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)
    op.drop_constraint("fk_invite_tokens_regenerated_from_invite_id", "invite_tokens", type_="foreignkey")
    op.drop_index(op.f("ix_invite_tokens_regenerated_from_invite_id"), table_name="invite_tokens")
    op.drop_index(op.f("ix_invite_tokens_token"), table_name="invite_tokens")
    op.drop_column("invite_tokens", "regenerated_from_invite_id")
    op.drop_column("invite_tokens", "status")
    op.drop_column("invite_tokens", "candidate_name")
    op.drop_column("invite_tokens", "token")
