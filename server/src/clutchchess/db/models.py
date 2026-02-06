"""Database models for Clutch Chess."""

from datetime import datetime

from fastapi_users.db import SQLAlchemyBaseOAuthAccountTable, SQLAlchemyBaseUserTable
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class OAuthAccount(SQLAlchemyBaseOAuthAccountTable[int], Base):
    """OAuth account linked to a user."""

    __tablename__ = "oauth_accounts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )


class User(SQLAlchemyBaseUserTable[int], Base):
    """User model supporting both email/password and Google OAuth.

    Attributes:
        id: Unique identifier (BIGINT for legacy compatibility)
        email: User email (optional for potential future username-only accounts)
        hashed_password: Password hash (NULL for Google-only users)
        is_active: Whether the user can login
        is_verified: Whether the email has been verified
        is_superuser: Admin privileges
        username: Display name (auto-generated if not provided)
        picture_url: Profile picture URL (from Google or uploaded)
        google_id: Google OAuth identifier for legacy user lookup
        ratings: Game ratings by mode (e.g. {"standard": 1200})
        created_at: Account creation timestamp
        last_online: Last activity timestamp
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # FastAPI-Users required fields
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Application-specific fields
    username: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    picture_url: Mapped[str | None] = mapped_column(String, nullable=True)
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    ratings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    last_online: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )

    # Relationship to OAuth accounts
    oauth_accounts: Mapped[list[OAuthAccount]] = relationship("OAuthAccount", lazy="joined")


class Lobby(Base):
    """Database model for game lobbies.

    Attributes:
        id: Unique identifier
        code: Short join code (e.g., "ABC123")
        host_id: User ID of the lobby host (NULL for anonymous hosts)
        speed: Game speed ("standard" or "lightning")
        player_count: Number of players (2 or 4)
        is_public: Whether the lobby appears in public listings
        is_ranked: Whether the game affects ELO ratings
        status: Lobby lifecycle status ("waiting", "in_game", "finished")
        game_id: ID of current/last game
        created_at: When the lobby was created
        started_at: When the game started
        finished_at: When the game finished
    """

    __tablename__ = "lobbies"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    host_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    speed: Mapped[str] = mapped_column(String(20), nullable=False, default="standard")
    player_count: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_ranked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="waiting", index=True
    )
    game_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False, index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    host: Mapped["User | None"] = relationship("User", foreign_keys=[host_id])
    players: Mapped[list["LobbyPlayer"]] = relationship(
        "LobbyPlayer", back_populates="lobby", cascade="all, delete-orphan"
    )

    # Composite index for list_public_waiting() queries
    __table_args__ = (
        Index("ix_lobbies_public_waiting", "is_public", "status", "created_at"),
    )


class LobbyPlayer(Base):
    """Database model for players in a lobby.

    Attributes:
        id: Unique identifier
        lobby_id: Foreign key to the lobby
        user_id: User ID (NULL for anonymous players)
        guest_id: Guest identifier for anonymous players
        player_slot: Slot number (1-4)
        username: Display name
        is_ready: Whether the player is ready
        is_ai: Whether this is an AI player
        ai_type: AI type identifier (e.g., "bot:novice")
        joined_at: When the player joined
    """

    __tablename__ = "lobby_players"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    lobby_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("lobbies.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    guest_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    player_slot: Mapped[int] = mapped_column(Integer, nullable=False)
    username: Mapped[str] = mapped_column(String(32), nullable=False)
    is_ready: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_ai: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ai_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )

    # Relationships
    lobby: Mapped["Lobby"] = relationship("Lobby", back_populates="players")
    user: Mapped["User | None"] = relationship("User", foreign_keys=[user_id])

    # Constraints
    __table_args__ = (
        UniqueConstraint("lobby_id", "player_slot", name="uq_lobby_players_lobby_slot"),
    )


class GameReplay(Base):
    """Stored replay for a completed game.

    Attributes:
        id: Unique identifier (same as game_id)
        speed: Game speed setting ("standard" or "lightning")
        board_type: Type of board ("standard" or "four_player")
        players: Map of player number to player ID
        moves: List of replay moves
        total_ticks: Total game duration in ticks
        winner: Winner (0=draw, 1-4=player number, None=unknown)
        win_reason: Reason for game end (e.g., "king_captured", "draw_no_moves")
        created_at: When the game was completed
        is_public: Whether the replay is publicly viewable
    """

    __tablename__ = "game_replays"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    speed: Mapped[str] = mapped_column(String, nullable=False)
    board_type: Mapped[str] = mapped_column(String, nullable=False)
    players: Mapped[dict] = mapped_column(JSON, nullable=False)
    moves: Mapped[list] = mapped_column(JSON, nullable=False)
    total_ticks: Mapped[int] = mapped_column(Integer, nullable=False)
    winner: Mapped[int | None] = mapped_column(Integer, nullable=True)
    win_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    tick_rate_hz: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    like_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_ranked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    campaign_level_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    initial_board_str: Mapped[str | None] = mapped_column(Text, nullable=True)


class ReplayLike(Base):
    """Records a user's like on a replay.

    Attributes:
        id: Unique identifier
        replay_id: Foreign key to game_replays.id
        user_id: Foreign key to users.id
        created_at: When the like was created
    """

    __tablename__ = "replay_likes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    replay_id: Mapped[str] = mapped_column(
        String, ForeignKey("game_replays.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("replay_id", "user_id", name="uq_replay_likes_replay_user"),
        Index("ix_replay_likes_replay_id", "replay_id"),
        Index("ix_replay_likes_user_id", "user_id"),
    )


class GameHistory(Base):
    """Legacy replay storage from original clutchchess.

    This table stores replays in the original format (single JSONB column).
    Used for backwards compatibility with legacy replays.

    Attributes:
        id: Auto-incrementing primary key
        replay: Complete replay data in legacy JSONB format
    """

    __tablename__ = "game_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    replay: Mapped[dict] = mapped_column(JSONB, nullable=False)


class UserGameHistory(Base):
    """Denormalized user match history for fast lookups.

    This table provides O(1) access to a user's match history via
    the (user_id, game_time) index. Each row represents one player's
    participation in a game.

    Attributes:
        id: Auto-incrementing primary key
        user_id: The user who played in this game
        game_time: When the game was played
        game_info: Game summary including:
            - speed: Game speed
            - player: This player's position (1-4)
            - winner: Winner position (0=draw)
            - historyId: ID of game_history entry (for legacy replays)
            - gameId: ID of game_replays entry (for new replays)
            - ticks: Game duration
            - opponents: List of opponent identifiers
    """

    __tablename__ = "user_game_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    game_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    game_info: Mapped[dict] = mapped_column(JSONB, nullable=False)


class CampaignProgress(Base):
    """User's campaign progress.

    Schema matches legacy clutchchess for backward compatibility.
    Progress is stored as JSONB with:
        - levelsCompleted: dict[str, bool] - level index → completed
        - beltsCompleted: dict[str, bool] - belt number → completed

    Attributes:
        id: Unique identifier
        user_id: Foreign key to users table (unique per user)
        progress: JSONB with levelsCompleted and beltsCompleted dicts
    """

    __tablename__ = "campaign_progress"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    progress: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class ActiveGame(Base):
    """Registry of currently running games.

    Transient table tracking all active games across server instances.
    Games register on creation and deregister on completion.
    """

    __tablename__ = "active_games"

    game_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    game_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    speed: Mapped[str] = mapped_column(String(20), nullable=False)
    player_count: Mapped[int] = mapped_column(Integer, nullable=False)
    board_type: Mapped[str] = mapped_column(String(20), nullable=False)
    players: Mapped[list] = mapped_column(JSON, nullable=False)
    lobby_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    campaign_level_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    server_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
