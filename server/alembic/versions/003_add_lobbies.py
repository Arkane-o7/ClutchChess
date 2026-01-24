"""Add lobbies and lobby_players tables.

Revision ID: 003_add_lobbies
Revises: 002_add_users
Create Date: 2025-01-23

This migration creates the tables needed for the lobby system.
Lobbies are waiting rooms where players gather before starting a game.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_add_lobbies"
down_revision: str | None = "002_add_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create lobbies and lobby_players tables."""
    # Create lobbies table
    op.create_table(
        "lobbies",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("code", sa.String(10), nullable=False),
        sa.Column("host_id", sa.BigInteger(), nullable=True),
        sa.Column("speed", sa.String(20), nullable=False, server_default="standard"),
        sa.Column("player_count", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_ranked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("status", sa.String(20), nullable=False, server_default="waiting"),
        sa.Column("game_id", sa.String(50), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["host_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint("code", name="uq_lobbies_code"),
    )

    # Create indexes for lobbies
    op.create_index("ix_lobbies_code", "lobbies", ["code"])
    op.create_index("ix_lobbies_status", "lobbies", ["status"])
    op.create_index("ix_lobbies_is_public", "lobbies", ["is_public"])

    # Create lobby_players table
    op.create_table(
        "lobby_players",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("lobby_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("guest_id", sa.String(50), nullable=True),
        sa.Column("player_slot", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("is_ready", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_ai", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("ai_type", sa.String(50), nullable=True),
        sa.Column(
            "joined_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["lobby_id"], ["lobbies.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint(
            "lobby_id", "player_slot", name="uq_lobby_players_lobby_slot"
        ),
    )

    # Create indexes for lobby_players
    op.create_index("ix_lobby_players_lobby_id", "lobby_players", ["lobby_id"])
    op.create_index("ix_lobby_players_user_id", "lobby_players", ["user_id"])
    op.create_index("ix_lobby_players_guest_id", "lobby_players", ["guest_id"])


def downgrade() -> None:
    """Drop lobbies and lobby_players tables."""
    # Drop lobby_players table
    op.drop_index("ix_lobby_players_guest_id", "lobby_players")
    op.drop_index("ix_lobby_players_user_id", "lobby_players")
    op.drop_index("ix_lobby_players_lobby_id", "lobby_players")
    op.drop_table("lobby_players")

    # Drop lobbies table
    op.drop_index("ix_lobbies_is_public", "lobbies")
    op.drop_index("ix_lobbies_status", "lobbies")
    op.drop_index("ix_lobbies_code", "lobbies")
    op.drop_table("lobbies")
