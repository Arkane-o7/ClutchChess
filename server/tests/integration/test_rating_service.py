"""Integration tests for the rating service.

These tests use a real database to verify the rating service works correctly
with actual user records and transactions.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from clutchchess.db.models import User
from clutchchess.game.elo import DEFAULT_RATING
from clutchchess.game.engine import GameEngine
from clutchchess.game.state import GameStatus, Speed, WinReason
from clutchchess.lobby.models import Lobby, LobbyPlayer, LobbySettings
from clutchchess.services.rating_service import RatingService, get_user_rating_stats


@pytest.fixture
async def test_users(db_session: AsyncSession) -> tuple[User, User]:
    """Create two test users for rating tests."""
    user1 = User(
        email="rating_test_user1@example.com",
        hashed_password="test_hash_1",
        is_active=True,
        is_verified=True,
        username="RatingTestUser1",
        ratings={},
    )
    user2 = User(
        email="rating_test_user2@example.com",
        hashed_password="test_hash_2",
        is_active=True,
        is_verified=True,
        username="RatingTestUser2",
        ratings={},
    )
    db_session.add(user1)
    db_session.add(user2)
    await db_session.flush()

    yield user1, user2

    # Cleanup
    await db_session.delete(user1)
    await db_session.delete(user2)
    await db_session.commit()


@pytest.fixture
async def test_users_with_ratings(db_session: AsyncSession) -> tuple[User, User]:
    """Create two test users with existing ratings."""
    user1 = User(
        email="rated_user1@example.com",
        hashed_password="test_hash_1",
        is_active=True,
        is_verified=True,
        username="RatedUser1",
        ratings={
            "2p_standard": {"rating": 1400, "games": 20, "wins": 12},
            "2p_lightning": {"rating": 1300, "games": 10, "wins": 5},
        },
    )
    user2 = User(
        email="rated_user2@example.com",
        hashed_password="test_hash_2",
        is_active=True,
        is_verified=True,
        username="RatedUser2",
        ratings={
            "2p_standard": {"rating": 1200, "games": 15, "wins": 7},
            "2p_lightning": {"rating": 1250, "games": 8, "wins": 4},
        },
    )
    db_session.add(user1)
    db_session.add(user2)
    await db_session.flush()

    yield user1, user2

    # Cleanup
    await db_session.delete(user1)
    await db_session.delete(user2)
    await db_session.commit()


def create_test_lobby(
    user1_id: int,
    user2_id: int,
    is_ranked: bool = True,
    speed: str = "standard",
) -> Lobby:
    """Create a test lobby with two players."""
    settings = LobbySettings(
        is_public=True,
        speed=speed,
        player_count=2,
        is_ranked=is_ranked,
    )
    lobby = Lobby(
        id=1,
        code="TEST01",
        host_slot=1,
        settings=settings,
    )
    lobby.players[1] = LobbyPlayer(
        slot=1,
        user_id=user1_id,
        username="Player1",
    )
    lobby.players[2] = LobbyPlayer(
        slot=2,
        user_id=user2_id,
        username="Player2",
    )
    return lobby


def create_finished_game_state(winner: int = 1):
    """Create a finished game state with the specified winner."""
    state = GameEngine.create_game(
        speed=Speed.STANDARD,
        players={1: "u:1", 2: "u:2"},
    )
    state, _ = GameEngine.set_player_ready(state, 1)
    state, _ = GameEngine.set_player_ready(state, 2)

    # Simulate game ending
    state.status = GameStatus.FINISHED
    state.winner = winner
    state.win_reason = WinReason.KING_CAPTURED

    return state


class TestRatingServiceIntegration:
    """Integration tests for RatingService with real database."""

    @pytest.mark.asyncio
    async def test_update_ratings_new_users(
        self, db_session: AsyncSession, test_users: tuple[User, User]
    ):
        """Test rating update for users with no prior ratings."""
        user1, user2 = test_users
        lobby = create_test_lobby(user1.id, user2.id)
        game_state = create_finished_game_state(winner=1)
        player_user_ids = {1: user1.id, 2: user2.id}

        service = RatingService(db_session)
        changes = await service.update_ratings_for_game(
            game_id="TEST001",
            game_state=game_state,
            lobby=lobby,
            player_user_ids=player_user_ids,
        )

        assert changes is not None
        assert len(changes) == 2

        # Winner should gain rating
        assert changes[1].old_rating == DEFAULT_RATING
        assert changes[1].new_rating > DEFAULT_RATING

        # Loser should lose rating
        assert changes[2].old_rating == DEFAULT_RATING
        assert changes[2].new_rating < DEFAULT_RATING

        # Commit and verify database was updated
        await db_session.commit()

        # Re-fetch users to verify database state
        result1 = await db_session.execute(select(User).where(User.id == user1.id))
        updated_user1 = result1.unique().scalar_one()
        result2 = await db_session.execute(select(User).where(User.id == user2.id))
        updated_user2 = result2.unique().scalar_one()

        stats1 = get_user_rating_stats(updated_user1, 2, "standard")
        stats2 = get_user_rating_stats(updated_user2, 2, "standard")

        assert stats1.rating == changes[1].new_rating
        assert stats1.games == 1
        assert stats1.wins == 1

        assert stats2.rating == changes[2].new_rating
        assert stats2.games == 1
        assert stats2.wins == 0

    @pytest.mark.asyncio
    async def test_update_ratings_existing_users(
        self, db_session: AsyncSession, test_users_with_ratings: tuple[User, User]
    ):
        """Test rating update for users with existing ratings."""
        user1, user2 = test_users_with_ratings
        lobby = create_test_lobby(user1.id, user2.id)
        game_state = create_finished_game_state(winner=2)  # Lower rated player wins
        player_user_ids = {1: user1.id, 2: user2.id}

        service = RatingService(db_session)
        changes = await service.update_ratings_for_game(
            game_id="TEST002",
            game_state=game_state,
            lobby=lobby,
            player_user_ids=player_user_ids,
        )

        assert changes is not None

        # Higher rated player (1400) loses to lower rated (1200)
        # Should result in larger rating change (upset)
        assert changes[1].old_rating == 1400
        assert changes[1].new_rating < 1400

        assert changes[2].old_rating == 1200
        assert changes[2].new_rating > 1200

        # Verify game counts incremented
        await db_session.commit()

        result1 = await db_session.execute(select(User).where(User.id == user1.id))
        updated_user1 = result1.unique().scalar_one()
        result2 = await db_session.execute(select(User).where(User.id == user2.id))
        updated_user2 = result2.unique().scalar_one()

        stats1 = get_user_rating_stats(updated_user1, 2, "standard")
        stats2 = get_user_rating_stats(updated_user2, 2, "standard")

        assert stats1.games == 21  # Was 20
        assert stats1.wins == 12  # Unchanged (lost)

        assert stats2.games == 16  # Was 15
        assert stats2.wins == 8  # Was 7 (won)

    @pytest.mark.asyncio
    async def test_update_ratings_draw(
        self, db_session: AsyncSession, test_users: tuple[User, User]
    ):
        """Test rating update on draw."""
        user1, user2 = test_users
        lobby = create_test_lobby(user1.id, user2.id)
        game_state = create_finished_game_state(winner=0)  # Draw
        game_state.win_reason = WinReason.DRAW
        player_user_ids = {1: user1.id, 2: user2.id}

        service = RatingService(db_session)
        changes = await service.update_ratings_for_game(
            game_id="TEST003",
            game_state=game_state,
            lobby=lobby,
            player_user_ids=player_user_ids,
        )

        assert changes is not None

        # Equal ratings, draw = no change
        assert changes[1].old_rating == DEFAULT_RATING
        assert changes[1].new_rating == DEFAULT_RATING
        assert changes[2].old_rating == DEFAULT_RATING
        assert changes[2].new_rating == DEFAULT_RATING

        # But games should still be counted
        await db_session.commit()

        result1 = await db_session.execute(select(User).where(User.id == user1.id))
        updated_user1 = result1.unique().scalar_one()

        stats1 = get_user_rating_stats(updated_user1, 2, "standard")
        assert stats1.games == 1
        assert stats1.wins == 0  # Draw doesn't count as win

    @pytest.mark.asyncio
    async def test_update_ratings_unranked_returns_none(
        self, db_session: AsyncSession, test_users: tuple[User, User]
    ):
        """Test that unranked games return None."""
        user1, user2 = test_users
        lobby = create_test_lobby(user1.id, user2.id, is_ranked=False)
        game_state = create_finished_game_state(winner=1)
        player_user_ids = {1: user1.id, 2: user2.id}

        service = RatingService(db_session)
        changes = await service.update_ratings_for_game(
            game_id="TEST004",
            game_state=game_state,
            lobby=lobby,
            player_user_ids=player_user_ids,
        )

        assert changes is None

    @pytest.mark.asyncio
    async def test_update_ratings_lightning_mode(
        self, db_session: AsyncSession, test_users_with_ratings: tuple[User, User]
    ):
        """Test rating update for lightning mode uses correct rating key."""
        user1, user2 = test_users_with_ratings
        lobby = create_test_lobby(user1.id, user2.id, speed="lightning")
        game_state = create_finished_game_state(winner=1)
        game_state.speed = Speed.LIGHTNING
        player_user_ids = {1: user1.id, 2: user2.id}

        service = RatingService(db_session)
        changes = await service.update_ratings_for_game(
            game_id="TEST005",
            game_state=game_state,
            lobby=lobby,
            player_user_ids=player_user_ids,
        )

        assert changes is not None

        # Should use lightning ratings (1300 vs 1250)
        assert changes[1].old_rating == 1300
        assert changes[2].old_rating == 1250

        await db_session.commit()

        result1 = await db_session.execute(select(User).where(User.id == user1.id))
        updated_user1 = result1.unique().scalar_one()

        # Standard rating should be unchanged
        stats_standard = get_user_rating_stats(updated_user1, 2, "standard")
        assert stats_standard.rating == 1400  # Unchanged
        assert stats_standard.games == 20  # Unchanged

        # Lightning rating should be updated
        stats_lightning = get_user_rating_stats(updated_user1, 2, "lightning")
        assert stats_lightning.rating == changes[1].new_rating
        assert stats_lightning.games == 11  # Was 10

    @pytest.mark.asyncio
    async def test_belt_change_tracked(
        self, db_session: AsyncSession, test_users: tuple[User, User]
    ):
        """Test that belt changes are correctly tracked."""
        user1, user2 = test_users

        # Set user1 right at belt boundary (1099 yellow, 1100 green)
        user1.ratings = {"2p_standard": {"rating": 1099, "games": 10, "wins": 5}}
        await db_session.flush()

        lobby = create_test_lobby(user1.id, user2.id)
        game_state = create_finished_game_state(winner=1)
        player_user_ids = {1: user1.id, 2: user2.id}

        service = RatingService(db_session)
        changes = await service.update_ratings_for_game(
            game_id="TEST006",
            game_state=game_state,
            lobby=lobby,
            player_user_ids=player_user_ids,
        )

        assert changes is not None

        # User1 should go from yellow to green
        assert changes[1].old_belt == "yellow"
        assert changes[1].new_belt == "green"
        assert changes[1].belt_changed is True

    @pytest.mark.asyncio
    async def test_abandoned_game_not_rated(
        self, db_session: AsyncSession, test_users: tuple[User, User]
    ):
        """Test that abandoned games don't update ratings."""
        user1, user2 = test_users
        lobby = create_test_lobby(user1.id, user2.id)
        game_state = create_finished_game_state(winner=1)
        game_state.win_reason = WinReason.INVALID  # Not a rated win reason
        player_user_ids = {1: user1.id, 2: user2.id}

        service = RatingService(db_session)
        changes = await service.update_ratings_for_game(
            game_id="TEST007",
            game_state=game_state,
            lobby=lobby,
            player_user_ids=player_user_ids,
        )

        assert changes is None
