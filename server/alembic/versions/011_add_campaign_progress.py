"""Add campaign progress table.

Revision ID: 011_add_campaign_progress
Revises: 010_add_replay_top_index
Create Date: 2026-02-03

Creates the campaign_progress table for storing user campaign progress.
Schema matches legacy clutchchess for backward compatibility.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "011_add_campaign_progress"
down_revision: str | None = "010_add_replay_top_index"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create campaign_progress table."""
    op.create_table(
        "campaign_progress",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("progress", JSONB(), nullable=False, server_default="{}"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_campaign_progress_user_id"),
    )
    op.create_index(
        "ix_campaign_progress_user_id", "campaign_progress", ["user_id"]
    )


def downgrade() -> None:
    """Drop campaign_progress table."""
    op.drop_index("ix_campaign_progress_user_id", "campaign_progress")
    op.drop_table("campaign_progress")
