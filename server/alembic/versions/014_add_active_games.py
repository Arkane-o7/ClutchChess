"""Add active_games registry table.

Revision ID: 014_add_active_games
Revises: 013_add_replay_initial_board
Create Date: 2026-02-04

Adds a database-backed registry for all currently running games,
enabling the Live Games feature to work across server instances
and for all game types (lobby, campaign, quickplay).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "014_add_active_games"
down_revision: str | None = "013_add_replay_initial_board"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create active_games table."""
    op.create_table(
        "active_games",
        sa.Column("game_id", sa.String(50), nullable=False),
        sa.Column("game_type", sa.String(20), nullable=False),
        sa.Column("speed", sa.String(20), nullable=False),
        sa.Column("player_count", sa.Integer(), nullable=False),
        sa.Column("board_type", sa.String(20), nullable=False),
        sa.Column("players", sa.JSON(), nullable=False),
        sa.Column("lobby_code", sa.String(10), nullable=True),
        sa.Column("campaign_level_id", sa.Integer(), nullable=True),
        sa.Column(
            "started_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("server_id", sa.String(100), nullable=False),
        sa.PrimaryKeyConstraint("game_id"),
    )

    op.create_index("ix_active_games_game_type", "active_games", ["game_type"])
    op.create_index("ix_active_games_server_id", "active_games", ["server_id"])


def downgrade() -> None:
    """Drop active_games table."""
    op.drop_index("ix_active_games_server_id", "active_games")
    op.drop_index("ix_active_games_game_type", "active_games")
    op.drop_table("active_games")
