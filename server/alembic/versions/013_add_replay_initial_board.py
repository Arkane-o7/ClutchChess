"""Add initial_board_str to game_replays.

Revision ID: 013_add_replay_initial_board
Revises: 012_add_replay_campaign_level
Create Date: 2026-02-04

Adds initial_board_str column to store the initial board configuration for
campaign games, allowing replays to start from custom boards.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "013_add_replay_initial_board"
down_revision: str | None = "012_add_replay_campaign_level"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add initial_board_str column to game_replays."""
    op.add_column(
        "game_replays",
        sa.Column("initial_board_str", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Remove initial_board_str column from game_replays."""
    op.drop_column("game_replays", "initial_board_str")
