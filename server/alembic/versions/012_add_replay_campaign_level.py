"""Add campaign_level_id to game_replays.

Revision ID: 012_add_replay_campaign_level
Revises: 011_add_campaign_progress
Create Date: 2026-02-04

Adds campaign_level_id column to track which campaign level a replay came from.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "012_add_replay_campaign_level"
down_revision: str | None = "011_add_campaign_progress"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add campaign_level_id column to game_replays."""
    op.add_column(
        "game_replays",
        sa.Column("campaign_level_id", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    """Remove campaign_level_id column from game_replays."""
    op.drop_column("game_replays", "campaign_level_id")
