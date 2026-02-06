"""Add legacy replay tables for backwards compatibility.

Adds game_history and user_game_history tables from the original
clutchchess implementation to support:
1. Loading legacy replays
2. O(1) user match history lookups via indexed user_game_history table

Revision ID: 006_add_legacy_replay_tables
Revises: 177687c383a4
Create Date: 2025-01-27

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006_add_legacy_replay_tables"
down_revision: str | None = "177687c383a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create legacy replay tables."""
    # game_history - stores complete replay data (legacy format)
    # This matches the original clutchchess schema exactly
    op.create_table(
        "game_history",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "replay", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # user_game_history - denormalized table for fast user match history lookups
    # Indexed by (user_id, game_time) for efficient queries
    op.create_table(
        "user_game_history",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("game_time", sa.DateTime(), nullable=False),
        sa.Column(
            "game_info", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create composite index for efficient user history queries
    # This is the key optimization - allows O(1) lookup of user's games
    op.create_index(
        "ix_user_game_history_user_id_game_time",
        "user_game_history",
        ["user_id", sa.text("game_time DESC")],
    )


def downgrade() -> None:
    """Drop legacy replay tables."""
    op.drop_index("ix_user_game_history_user_id_game_time", "user_game_history")
    op.drop_table("user_game_history")
    op.drop_table("game_history")
