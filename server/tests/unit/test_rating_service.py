"""Tests for the rating service."""

from unittest.mock import MagicMock

from clutchchess.game.elo import DEFAULT_RATING
from clutchchess.game.state import WinReason
from clutchchess.lobby.models import Lobby, LobbyPlayer, LobbySettings
from clutchchess.services.rating_service import (
    RatingService,
    get_user_rating,
    get_user_rating_stats,
)


class MockGameState:
    """Mock game state for testing."""

    def __init__(self, win_reason: WinReason | None = WinReason.KING_CAPTURED) -> None:
        self.win_reason = win_reason
        self.winner = 1 if win_reason else None


class MockUser:
    """Mock user object for testing."""

    def __init__(self, ratings: dict | None = None) -> None:
        self.ratings = ratings or {}


class TestGetUserRatingStats:
    """Tests for get_user_rating_stats helper."""

    def test_no_ratings_returns_default(self):
        """User with no ratings should get default stats."""
        user = MockUser()
        stats = get_user_rating_stats(user, 2, "standard")  # type: ignore
        assert stats.rating == DEFAULT_RATING
        assert stats.games == 0
        assert stats.wins == 0

    def test_empty_ratings_returns_default(self):
        """User with empty ratings dict should get default stats."""
        user = MockUser(ratings={})
        stats = get_user_rating_stats(user, 2, "standard")  # type: ignore
        assert stats.rating == DEFAULT_RATING
        assert stats.games == 0
        assert stats.wins == 0

    def test_existing_ratings_returned(self):
        """User with existing ratings should get those stats."""
        user = MockUser(
            ratings={
                "2p_standard": {"rating": 1500, "games": 50, "wins": 30},
                "2p_lightning": {"rating": 1400, "games": 20, "wins": 12},
            }
        )
        stats = get_user_rating_stats(user, 2, "standard")  # type: ignore
        assert stats.rating == 1500
        assert stats.games == 50
        assert stats.wins == 30

    def test_4p_mode(self):
        """Test getting 4-player mode stats."""
        user = MockUser(
            ratings={
                "4p_standard": {"rating": 1350, "games": 10, "wins": 5},
            }
        )
        stats = get_user_rating_stats(user, 4, "standard")  # type: ignore
        assert stats.rating == 1350
        assert stats.games == 10
        assert stats.wins == 5

    def test_missing_mode_returns_default(self):
        """User with ratings but not for requested mode should get default."""
        user = MockUser(
            ratings={
                "2p_standard": {"rating": 1500, "games": 50, "wins": 30},
            }
        )
        # Request 4p mode which doesn't exist
        stats = get_user_rating_stats(user, 4, "lightning")  # type: ignore
        assert stats.rating == DEFAULT_RATING
        assert stats.games == 0
        assert stats.wins == 0

    def test_partial_stats_uses_defaults(self):
        """Stats with missing fields should use defaults for those fields."""
        user = MockUser(
            ratings={
                "2p_standard": {"rating": 1500},  # Missing games and wins
            }
        )
        stats = get_user_rating_stats(user, 2, "standard")  # type: ignore
        assert stats.rating == 1500
        assert stats.games == 0  # Default
        assert stats.wins == 0  # Default


class TestGetUserRating:
    """Tests for get_user_rating convenience function."""

    def test_returns_rating_value(self):
        """Should return just the rating integer."""
        user = MockUser(
            ratings={
                "2p_standard": {"rating": 1600, "games": 10, "wins": 5},
            }
        )
        rating = get_user_rating(user, 2, "standard")  # type: ignore
        assert rating == 1600

    def test_returns_default_when_missing(self):
        """Should return default rating when mode is missing."""
        user = MockUser()
        rating = get_user_rating(user, 2, "standard")  # type: ignore
        assert rating == DEFAULT_RATING


class TestRatingServiceEligibility:
    """Tests for RatingService._is_eligible method."""

    def _create_lobby(
        self,
        is_ranked: bool = True,
        has_ai: bool = False,
        has_guest: bool = False,
        player_count: int = 2,
    ) -> Lobby:
        """Create a test lobby with specified characteristics."""
        settings = LobbySettings(
            is_public=True,
            speed="standard",
            player_count=player_count,
            is_ranked=is_ranked,
        )
        lobby = Lobby(
            id=1,
            code="TEST01",
            host_slot=1,
            settings=settings,
        )

        # Add players
        lobby.players[1] = LobbyPlayer(
            slot=1,
            user_id=100,
            username="Player1",
        )
        lobby.players[2] = LobbyPlayer(
            slot=2,
            user_id=None if has_guest else 200,
            username="Player2" if not has_ai else "AI (dummy)",
            is_ai=has_ai,
            ai_type="bot:dummy" if has_ai else None,
        )

        if player_count == 4:
            lobby.players[3] = LobbyPlayer(
                slot=3,
                user_id=300,
                username="Player3",
            )
            lobby.players[4] = LobbyPlayer(
                slot=4,
                user_id=400,
                username="Player4",
            )

        return lobby

    def _create_service(self) -> RatingService:
        """Create a rating service with mock session."""
        mock_session = MagicMock()
        return RatingService(mock_session)

    def _create_game_state(
        self, win_reason: WinReason | None = WinReason.KING_CAPTURED
    ) -> MockGameState:
        """Create a mock game state."""
        return MockGameState(win_reason=win_reason)

    def test_unranked_game_not_eligible(self):
        """Unranked games should not be eligible for rating updates."""
        service = self._create_service()
        game_state = self._create_game_state()
        lobby = self._create_lobby(is_ranked=False)
        player_user_ids = {1: 100, 2: 200}

        result = service._is_eligible(game_state, lobby, player_user_ids)  # type: ignore
        assert result is False

    def test_ranked_game_eligible(self):
        """Ranked games with all humans should be eligible."""
        service = self._create_service()
        game_state = self._create_game_state()
        lobby = self._create_lobby(is_ranked=True)
        player_user_ids = {1: 100, 2: 200}

        result = service._is_eligible(game_state, lobby, player_user_ids)  # type: ignore
        assert result is True

    def test_game_with_ai_not_eligible(self):
        """Games with AI players should not be eligible."""
        service = self._create_service()
        game_state = self._create_game_state()
        lobby = self._create_lobby(is_ranked=True, has_ai=True)
        player_user_ids = {1: 100}  # AI doesn't have user_id

        result = service._is_eligible(game_state, lobby, player_user_ids)  # type: ignore
        assert result is False

    def test_game_with_guest_not_eligible(self):
        """Games with guest players should not be eligible."""
        service = self._create_service()
        game_state = self._create_game_state()
        lobby = self._create_lobby(is_ranked=True, has_guest=True)
        player_user_ids = {1: 100}  # Guest doesn't have user_id in lobby

        result = service._is_eligible(game_state, lobby, player_user_ids)  # type: ignore
        assert result is False

    def test_player_mismatch_not_eligible(self):
        """Mismatched player_user_ids should not be eligible."""
        service = self._create_service()
        game_state = self._create_game_state()
        lobby = self._create_lobby(is_ranked=True)
        # Missing player 2
        player_user_ids = {1: 100}

        result = service._is_eligible(game_state, lobby, player_user_ids)  # type: ignore
        assert result is False

    def test_4p_ranked_eligible(self):
        """4-player ranked games should be eligible."""
        service = self._create_service()
        game_state = self._create_game_state()
        lobby = self._create_lobby(is_ranked=True, player_count=4)
        player_user_ids = {1: 100, 2: 200, 3: 300, 4: 400}

        result = service._is_eligible(game_state, lobby, player_user_ids)  # type: ignore
        assert result is True

    def test_invalid_win_reason_not_eligible(self):
        """Games ending with INVALID win reason should not be eligible."""
        service = self._create_service()
        game_state = self._create_game_state(win_reason=WinReason.INVALID)
        lobby = self._create_lobby(is_ranked=True)
        player_user_ids = {1: 100, 2: 200}

        result = service._is_eligible(game_state, lobby, player_user_ids)  # type: ignore
        assert result is False

    def test_all_rated_win_reasons_eligible(self):
        """All rated win reasons should be eligible."""
        service = self._create_service()
        lobby = self._create_lobby(is_ranked=True)
        player_user_ids = {1: 100, 2: 200}

        rated_reasons = [wr for wr in WinReason if wr.is_rated()]
        for win_reason in rated_reasons:
            game_state = self._create_game_state(win_reason=win_reason)
            result = service._is_eligible(game_state, lobby, player_user_ids)  # type: ignore
            assert result is True, f"Win reason '{win_reason}' should be eligible"

    def test_none_win_reason_not_eligible(self):
        """Games with None win_reason should not be eligible."""
        service = self._create_service()
        game_state = self._create_game_state(win_reason=None)
        lobby = self._create_lobby(is_ranked=True)
        player_user_ids = {1: 100, 2: 200}

        result = service._is_eligible(game_state, lobby, player_user_ids)  # type: ignore
        assert result is False
