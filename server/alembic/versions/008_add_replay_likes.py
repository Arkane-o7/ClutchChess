"""Add replay likes system.

Revision ID: 008_add_replay_likes
Revises: 1832246a958d
Create Date: 2026-02-03

Adds:
- replay_likes table for tracking individual likes
- like_count column on game_replays for fast sorting
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "008_add_replay_likes"
down_revision: str | None = "1832246a958d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add replay likes system."""
    # Add like_count column to game_replays with default of 0
    op.add_column(
        "game_replays",
        sa.Column("like_count", sa.Integer(), nullable=False, server_default="0"),
    )

    # Create index for sorting by likes
    op.create_index(
        "ix_game_replays_like_count",
        "game_replays",
        ["like_count"],
    )

    # Create replay_likes table
    op.create_table(
        "replay_likes",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("replay_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["replay_id"], ["game_replays.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("replay_id", "user_id", name="uq_replay_likes_replay_user"),
    )

    # Create indexes
    op.create_index("ix_replay_likes_replay_id", "replay_likes", ["replay_id"])
    op.create_index("ix_replay_likes_user_id", "replay_likes", ["user_id"])


def downgrade() -> None:
    """Remove replay likes system."""
    # Drop replay_likes table
    op.drop_index("ix_replay_likes_user_id", "replay_likes")
    op.drop_index("ix_replay_likes_replay_id", "replay_likes")
    op.drop_table("replay_likes")

    # Drop like_count column
    op.drop_index("ix_game_replays_like_count", "game_replays")
    op.drop_column("game_replays", "like_count")
