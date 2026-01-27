"""Add ELO rating system with new schema and leaderboard indexes.

Revision ID: 005_add_elo_rating
Revises: 004_add_lobby_indexes
Create Date: 2025-01-26

This migration:
1. Converts existing ratings JSONB from old format to new format with game stats
2. Adds functional indexes for efficient leaderboard queries on JSONB fields

Old format: {"standard": 1200, "lightning": 1350}
New format: {
    "2p_standard": {"rating": 1200, "games": 0, "wins": 0},
    "2p_lightning": {"rating": 1350, "games": 0, "wins": 0},
    "4p_standard": {"rating": 1200, "games": 0, "wins": 0},
    "4p_lightning": {"rating": 1200, "games": 0, "wins": 0}
}
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005_add_elo_rating"
down_revision: str | None = "004_add_lobby_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Convert ratings format and add leaderboard indexes."""
    # Convert old rating format to new format with game stats
    # Only update users who have existing ratings in the old format
    op.execute("""
        UPDATE users
        SET ratings = jsonb_build_object(
            '2p_standard', jsonb_build_object(
                'rating', COALESCE((ratings->>'standard')::int, 1200),
                'games', 0,
                'wins', 0
            ),
            '2p_lightning', jsonb_build_object(
                'rating', COALESCE((ratings->>'lightning')::int, 1200),
                'games', 0,
                'wins', 0
            ),
            '4p_standard', jsonb_build_object('rating', 1200, 'games', 0, 'wins', 0),
            '4p_lightning', jsonb_build_object('rating', 1200, 'games', 0, 'wins', 0)
        )
        WHERE ratings != '{}'::jsonb
          AND ratings ? 'standard'
    """)

    # Functional indexes for leaderboard queries on each rating mode
    # These enable efficient ORDER BY on the nested JSONB rating values
    op.execute("""
        CREATE INDEX idx_users_rating_2p_standard
        ON users (((ratings->'2p_standard'->>'rating')::int) DESC NULLS LAST)
        WHERE ratings ? '2p_standard'
    """)

    op.execute("""
        CREATE INDEX idx_users_rating_2p_lightning
        ON users (((ratings->'2p_lightning'->>'rating')::int) DESC NULLS LAST)
        WHERE ratings ? '2p_lightning'
    """)

    op.execute("""
        CREATE INDEX idx_users_rating_4p_standard
        ON users (((ratings->'4p_standard'->>'rating')::int) DESC NULLS LAST)
        WHERE ratings ? '4p_standard'
    """)

    op.execute("""
        CREATE INDEX idx_users_rating_4p_lightning
        ON users (((ratings->'4p_lightning'->>'rating')::int) DESC NULLS LAST)
        WHERE ratings ? '4p_lightning'
    """)

    # GIN index for general JSONB containment queries
    op.execute("""
        CREATE INDEX idx_users_ratings_gin ON users USING gin(ratings)
    """)


def downgrade() -> None:
    """Remove leaderboard indexes and revert to old rating format."""
    # Drop indexes
    op.execute("DROP INDEX IF EXISTS idx_users_ratings_gin")
    op.execute("DROP INDEX IF EXISTS idx_users_rating_4p_lightning")
    op.execute("DROP INDEX IF EXISTS idx_users_rating_4p_standard")
    op.execute("DROP INDEX IF EXISTS idx_users_rating_2p_lightning")
    op.execute("DROP INDEX IF EXISTS idx_users_rating_2p_standard")

    # Revert to old format (note: game counts will be lost)
    op.execute("""
        UPDATE users
        SET ratings = jsonb_build_object(
            'standard', COALESCE((ratings->'2p_standard'->>'rating')::int, 1200),
            'lightning', COALESCE((ratings->'2p_lightning'->>'rating')::int, 1200)
        )
        WHERE ratings ? '2p_standard'
    """)
