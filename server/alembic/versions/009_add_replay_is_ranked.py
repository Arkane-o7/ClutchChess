"""Add is_ranked column to game_replays.

Revision ID: 009_add_replay_is_ranked
Revises: 008_add_replay_likes
Create Date: 2026-02-03

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "009_add_replay_is_ranked"
down_revision: str | None = "008_add_replay_likes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "game_replays",
        sa.Column("is_ranked", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("game_replays", "is_ranked")
