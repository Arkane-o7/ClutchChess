"""Add composite index for top replays query.

Revision ID: 010_add_replay_top_index
Revises: 009_add_replay_is_ranked
Create Date: 2026-02-03

Adds composite index on (like_count DESC, created_at DESC) for efficient
sorting in the list_top() query.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "010_add_replay_top_index"
down_revision: str | None = "009_add_replay_is_ranked"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create composite index for list_top query
    # PostgreSQL requires explicit DESC for descending order in index
    op.create_index(
        "ix_game_replays_top",
        "game_replays",
        ["like_count", "created_at"],
        postgresql_ops={"like_count": "DESC", "created_at": "DESC"},
    )
    # Drop the old single-column index since the composite index covers it
    op.drop_index("ix_game_replays_like_count", "game_replays")


def downgrade() -> None:
    # Recreate the single-column index
    op.create_index(
        "ix_game_replays_like_count",
        "game_replays",
        ["like_count"],
    )
    # Drop the composite index
    op.drop_index("ix_game_replays_top", "game_replays")
