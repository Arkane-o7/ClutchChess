"""Update leaderboard indexes to include games > 0 filter.

Revision ID: 007_update_leaderboard_indexes
Revises: 177687c383a4
Create Date: 2026-01-30

The existing indexes from migration 005 filter on `ratings ? :mode` but
the leaderboard query also filters on games > 0. Adding this predicate
to the partial index lets Postgres satisfy a top-100 query with an
index-only scan.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "007_update_leaderboard_indexes"
down_revision: str | None = "177687c383a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MODES = ["2p_standard", "2p_lightning", "4p_standard", "4p_lightning"]


def upgrade() -> None:
    """Replace leaderboard indexes with ones that include games > 0 filter."""
    for mode in MODES:
        # Drop old index
        op.execute(f"DROP INDEX IF EXISTS idx_users_rating_{mode}")
        # Create new index with games > 0 predicate
        op.execute(f"""
            CREATE INDEX idx_users_rating_{mode}
            ON users (((ratings->'{mode}'->>'rating')::int) DESC NULLS LAST)
            WHERE ratings ? '{mode}'
              AND (ratings->'{mode}'->>'games')::int > 0
        """)


def downgrade() -> None:
    """Revert to indexes without games > 0 filter."""
    for mode in MODES:
        op.execute(f"DROP INDEX IF EXISTS idx_users_rating_{mode}")
        op.execute(f"""
            CREATE INDEX idx_users_rating_{mode}
            ON users (((ratings->'{mode}'->>'rating')::int) DESC NULLS LAST)
            WHERE ratings ? '{mode}'
        """)
