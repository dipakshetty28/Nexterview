"""scenario approval status

Revision ID: 0016_scenario_approval_status
Revises: 0015_multi_candidate_invites
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa

revision = "0016_scenario_approval_status"
down_revision = "0015_multi_candidate_invites"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scenarios", sa.Column("status", sa.String(length=40), nullable=False, server_default="draft"))
    op.execute("UPDATE scenarios SET status = 'approved'")


def downgrade() -> None:
    op.drop_column("scenarios", "status")
