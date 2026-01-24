"""Lobby domain models for Kung Fu Chess.

This module contains the core data structures for the lobby system.
Lobbies are waiting rooms where players gather before starting a game.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class LobbyStatus(Enum):
    """Lobby lifecycle status."""

    WAITING = "waiting"  # Waiting for players to join/ready
    IN_GAME = "in_game"  # Game is in progress (countdown + playing)
    FINISHED = "finished"  # Game ended, lobby still exists for rematch


@dataclass
class LobbyPlayer:
    """A player in a lobby.

    Attributes:
        slot: Player slot number (1-4)
        user_id: Database user ID (None for guests/anonymous)
        username: Display name
        is_ai: Whether this is an AI player
        ai_type: AI type identifier (e.g., "bot:dummy")
        is_ready: Whether the player is ready to start
        joined_at: When the player joined the lobby
    """

    slot: int
    user_id: int | None
    username: str
    is_ai: bool = False
    ai_type: str | None = None
    _is_ready: bool = field(default=False, repr=False)
    joined_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_ready(self) -> bool:
        """AI players are always ready."""
        if self.is_ai:
            return True
        return self._is_ready

    @is_ready.setter
    def is_ready(self, value: bool) -> None:
        """Set ready state (only affects non-AI players)."""
        self._is_ready = value


@dataclass
class LobbySettings:
    """Configurable lobby settings.

    Attributes:
        is_public: Whether the lobby appears in public listings
        speed: Game speed ("standard" or "lightning")
        player_count: Number of players (2 or 4)
        is_ranked: Whether the game affects ELO ratings
    """

    is_public: bool = True
    speed: str = "standard"
    player_count: int = 2
    is_ranked: bool = False

    def __post_init__(self) -> None:
        """Validate settings."""
        if self.speed not in ("standard", "lightning"):
            raise ValueError(f"Invalid speed: {self.speed}")
        if self.player_count not in (2, 4):
            raise ValueError(f"Invalid player_count: {self.player_count}")


@dataclass
class Lobby:
    """A game lobby.

    Attributes:
        id: Database ID
        code: Short join code (e.g., "ABC123")
        host_slot: Slot number of the host player
        settings: Lobby configuration
        players: Map of slot number to player
        status: Lobby lifecycle status
        current_game_id: ID of the current/last game
        games_played: Number of games played in this lobby
        created_at: When the lobby was created
        game_finished_at: When the last game finished (for cleanup)
    """

    id: int
    code: str
    host_slot: int
    settings: LobbySettings
    players: dict[int, LobbyPlayer] = field(default_factory=dict)
    status: LobbyStatus = LobbyStatus.WAITING
    current_game_id: str | None = None
    games_played: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    game_finished_at: datetime | None = None

    @property
    def host(self) -> LobbyPlayer | None:
        """Get the current host player."""
        return self.players.get(self.host_slot)

    @property
    def is_full(self) -> bool:
        """Check if all slots are filled."""
        return len(self.players) >= self.settings.player_count

    @property
    def all_ready(self) -> bool:
        """Check if all players are ready."""
        if len(self.players) < self.settings.player_count:
            return False
        return all(p.is_ready for p in self.players.values())

    @property
    def human_players(self) -> list[LobbyPlayer]:
        """Get all non-AI players."""
        return [p for p in self.players.values() if not p.is_ai]

    @property
    def ai_players(self) -> list[LobbyPlayer]:
        """Get all AI players."""
        return [p for p in self.players.values() if p.is_ai]

    def get_next_slot(self) -> int | None:
        """Get the next available slot number.

        Returns:
            The next available slot (1-based), or None if full.
        """
        for slot in range(1, self.settings.player_count + 1):
            if slot not in self.players:
                return slot
        return None

    def to_dict(self) -> dict:
        """Serialize lobby to a dictionary for API responses."""
        return {
            "id": self.id,
            "code": self.code,
            "hostSlot": self.host_slot,
            "settings": {
                "isPublic": self.settings.is_public,
                "speed": self.settings.speed,
                "playerCount": self.settings.player_count,
                "isRanked": self.settings.is_ranked,
            },
            "players": {
                slot: {
                    "slot": p.slot,
                    "userId": p.user_id,
                    "username": p.username,
                    "isAi": p.is_ai,
                    "aiType": p.ai_type,
                    "isReady": p.is_ready,
                }
                for slot, p in self.players.items()
            },
            "status": self.status.value,
            "currentGameId": self.current_game_id,
            "gamesPlayed": self.games_played,
        }
