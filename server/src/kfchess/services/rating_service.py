"""Rating service for updating player ELO ratings after games.

This service handles rating updates after ranked games complete, including:
- Eligibility checking (ranked, no AI, all logged in)
- Race condition protection via SELECT FOR UPDATE
- Atomic rating updates with game/win count tracking
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from kfchess.db.models import User
from kfchess.game.elo import (
    DEFAULT_RATING,
    RatingChange,
    UserRatingStats,
    get_belt,
    get_rating_key,
    update_ratings_2p,
    update_ratings_4p,
)
from kfchess.game.state import GameState
from kfchess.lobby.models import Lobby

logger = logging.getLogger(__name__)


def get_user_rating_stats(user: User, player_count: int, speed: str) -> UserRatingStats:
    """Get user's rating stats for a specific mode.

    Args:
        user: The user object
        player_count: Number of players (2 or 4)
        speed: Game speed ("standard" or "lightning")

    Returns:
        UserRatingStats for the specified mode
    """
    key = get_rating_key(player_count, speed)
    data = user.ratings.get(key) if user.ratings else None
    if data is None:
        return UserRatingStats.default()
    return UserRatingStats(
        rating=data.get("rating", DEFAULT_RATING),
        games=data.get("games", 0),
        wins=data.get("wins", 0),
    )


def get_user_rating(user: User, player_count: int, speed: str) -> int:
    """Get user's rating for a specific mode (convenience wrapper).

    Args:
        user: The user object
        player_count: Number of players (2 or 4)
        speed: Game speed ("standard" or "lightning")

    Returns:
        Rating for the specified mode
    """
    return get_user_rating_stats(user, player_count, speed).rating


class RatingService:
    """Service for updating player ratings after ranked games.

    This service is responsible for:
    - Checking if a game is eligible for rating updates
    - Calculating new ratings using ELO algorithm
    - Updating ratings atomically with proper locking
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the rating service.

        Args:
            session: SQLAlchemy async session for database operations
        """
        self.session = session

    async def update_ratings_for_game(
        self,
        game_id: str,
        game_state: GameState,
        lobby: Lobby,
        player_user_ids: dict[int, int],  # player_num -> user_id
    ) -> dict[int, RatingChange] | None:
        """Update ratings after a ranked game.

        Returns dict of {player_num: RatingChange} or None if not eligible.

        Uses SELECT FOR UPDATE to prevent race conditions when the same
        player finishes multiple games simultaneously.

        Args:
            game_id: The game ID (for logging)
            game_state: The finished game state
            lobby: The lobby the game was played in
            player_user_ids: Map of player number to user ID

        Returns:
            Dict mapping player_num to RatingChange, or None if game not eligible
        """
        # Check eligibility
        if not self._is_eligible(game_state, lobby, player_user_ids):
            return None

        player_count = lobby.settings.player_count
        speed = lobby.settings.speed
        rating_key = get_rating_key(player_count, speed)
        user_ids = list(player_user_ids.values())

        # Lock user rows to prevent concurrent rating updates
        # ORDER BY id prevents deadlocks when multiple games finish
        # Use noload to avoid LEFT OUTER JOIN with oauth_accounts (FOR UPDATE
        # doesn't work with nullable outer joins in PostgreSQL)
        stmt = (
            select(User)
            .options(noload(User.oauth_accounts))
            .where(User.id.in_(user_ids))
            .order_by(User.id)
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        users = {u.id: u for u in result.scalars().all()}

        # Verify all users found
        if len(users) != len(user_ids):
            logger.warning(
                f"Game {game_id}: Not all users found for rating update. "
                f"Expected {len(user_ids)}, found {len(users)}"
            )
            return None

        # Get current ratings
        current_stats = {
            player_num: get_user_rating_stats(users[user_id], player_count, speed)
            for player_num, user_id in player_user_ids.items()
        }
        current_ratings = {pn: stats.rating for pn, stats in current_stats.items()}

        # Calculate new ratings
        winner = game_state.winner or 0
        if player_count == 2:
            new_a, new_b = update_ratings_2p(
                current_ratings[1],
                current_ratings[2],
                winner,
            )
            new_ratings = {1: new_a, 2: new_b}
        else:
            new_ratings = update_ratings_4p(current_ratings, winner)

        # Update all users atomically
        for player_num, user_id in player_user_ids.items():
            user = users[user_id]
            old_stats = current_stats[player_num]
            new_rating = new_ratings[player_num]
            is_winner = game_state.winner == player_num

            # Update the nested JSONB structure
            # Create a new ratings dict to trigger SQLAlchemy change detection
            new_stats = {
                "rating": new_rating,
                "games": old_stats.games + 1,
                "wins": old_stats.wins + (1 if is_winner else 0),
            }
            user.ratings = {**(user.ratings or {}), rating_key: new_stats}

        logger.info(
            f"Game {game_id}: Rating updates - {', '.join(f'p{pn}: {current_ratings[pn]}->{new_ratings[pn]}' for pn in sorted(new_ratings))}"
        )

        # Return changes (session.commit() is caller's responsibility)
        return {
            player_num: RatingChange(
                old_rating=current_ratings[player_num],
                new_rating=new_ratings[player_num],
                old_belt=get_belt(current_ratings[player_num]),
                new_belt=get_belt(new_ratings[player_num]),
            )
            for player_num in player_user_ids
        }

    def _is_eligible(
        self,
        game_state: GameState,
        lobby: Lobby,
        player_user_ids: dict[int, int],
    ) -> bool:
        """Check if a game is eligible for rating updates.

        Args:
            game_state: The finished game state
            lobby: The lobby the game was played in
            player_user_ids: Map of player number to user ID

        Returns:
            True if the game should update ratings
        """
        # Must be a ranked game
        if not lobby.settings.is_ranked:
            logger.debug(f"Lobby {lobby.code}: Not ranked, skipping rating update")
            return False

        # Game must have ended with a rated win reason
        if game_state.win_reason is None or not game_state.win_reason.is_rated():
            logger.debug(
                f"Lobby {lobby.code}: Win reason '{game_state.win_reason}' not rated, "
                "skipping rating update"
            )
            return False

        # No AI players allowed
        if any(p.is_ai for p in lobby.players.values()):
            logger.debug(f"Lobby {lobby.code}: Has AI players, skipping rating update")
            return False

        # All players must have accounts (no guests)
        if any(p.user_id is None for p in lobby.players.values()):
            logger.debug(f"Lobby {lobby.code}: Has guest players, skipping rating update")
            return False

        # Verify we have user IDs for all players
        expected_players = set(lobby.players.keys())
        actual_players = set(player_user_ids.keys())
        if expected_players != actual_players:
            logger.warning(
                f"Lobby {lobby.code}: Player mismatch. "
                f"Expected {expected_players}, got {actual_players}"
            )
            return False

        return True
