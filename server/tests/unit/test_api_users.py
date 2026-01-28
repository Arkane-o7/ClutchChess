"""Tests for the users API endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from kfchess.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client."""
    return TestClient(app)


class TestGetPublicUserProfile:
    """Tests for GET /api/users/{user_id}."""

    def test_get_public_profile_returns_user(self, client: TestClient) -> None:
        """Test getting a public user profile."""
        mock_user = MagicMock()
        mock_user.id = 123
        mock_user.username = "testuser"
        mock_user.picture_url = "https://example.com/pic.jpg"
        mock_user.ratings = {"standard": 1500}
        mock_user.created_at = datetime.now(UTC)
        mock_user.last_online = datetime.now(UTC)

        with patch(
            "kfchess.api.users.UserRepository"
        ) as MockUserRepository:
            mock_repo = MockUserRepository.return_value
            mock_repo.get_by_id = AsyncMock(return_value=mock_user)

            response = client.get("/api/users/123")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 123
        assert data["username"] == "testuser"
        assert data["picture_url"] == "https://example.com/pic.jpg"
        assert data["ratings"] == {"standard": 1500}
        # Email should NOT be in public profile
        assert "email" not in data
        assert "is_verified" not in data

    def test_get_public_profile_not_found(self, client: TestClient) -> None:
        """Test getting a non-existent user."""
        with patch(
            "kfchess.api.users.UserRepository"
        ) as MockUserRepository:
            mock_repo = MockUserRepository.return_value
            mock_repo.get_by_id = AsyncMock(return_value=None)

            response = client.get("/api/users/999999")

        assert response.status_code == 404
        assert response.json()["detail"] == "User not found"

    def test_get_public_profile_with_null_ratings(self, client: TestClient) -> None:
        """Test getting a user profile with null ratings."""
        mock_user = MagicMock()
        mock_user.id = 123
        mock_user.username = "newuser"
        mock_user.picture_url = None
        mock_user.ratings = None  # New user with no ratings
        mock_user.created_at = datetime.now(UTC)
        mock_user.last_online = datetime.now(UTC)

        with patch(
            "kfchess.api.users.UserRepository"
        ) as MockUserRepository:
            mock_repo = MockUserRepository.return_value
            mock_repo.get_by_id = AsyncMock(return_value=mock_user)

            response = client.get("/api/users/123")

        assert response.status_code == 200
        data = response.json()
        assert data["ratings"] == {}  # Should be empty dict, not null


class TestGetUserReplays:
    """Tests for GET /api/users/{user_id}/replays."""

    def test_get_user_replays_returns_empty_list(self, client: TestClient) -> None:
        """Test getting replays for user with no games."""
        mock_user = MagicMock()
        mock_user.id = 123

        with patch(
            "kfchess.api.users.UserRepository"
        ) as MockUserRepository, patch(
            "kfchess.db.repositories.user_game_history.UserGameHistoryRepository"
        ) as MockHistoryRepository:
            mock_user_repo = MockUserRepository.return_value
            mock_user_repo.get_by_id = AsyncMock(return_value=mock_user)

            mock_history_repo = MockHistoryRepository.return_value
            mock_history_repo.list_by_user = AsyncMock(return_value=[])
            mock_history_repo.count_by_user = AsyncMock(return_value=0)

            response = client.get("/api/users/123/replays")

        assert response.status_code == 200
        data = response.json()
        assert data["replays"] == []
        assert data["total"] == 0

    def test_get_user_replays_returns_entries(self, client: TestClient) -> None:
        """Test getting replays returns match history entries."""
        mock_user = MagicMock()
        mock_user.id = 123

        mock_entry = MagicMock()
        mock_entry.game_time = datetime.now(UTC)
        mock_entry.game_info = {
            "speed": "standard",
            "boardType": "standard",
            "player": 1,
            "winner": 1,
            "winReason": "king_captured",
            "gameId": "ABC123",
            "ticks": 1500,
            "opponents": ["u:456"],
        }

        with patch(
            "kfchess.api.users.UserRepository"
        ) as MockUserRepository, patch(
            "kfchess.db.repositories.user_game_history.UserGameHistoryRepository"
        ) as MockHistoryRepository, patch(
            "kfchess.api.users.resolve_player_names"
        ) as mock_resolve:
            mock_user_repo = MockUserRepository.return_value
            mock_user_repo.get_by_id = AsyncMock(return_value=mock_user)

            mock_history_repo = MockHistoryRepository.return_value
            mock_history_repo.list_by_user = AsyncMock(return_value=[mock_entry])
            mock_history_repo.count_by_user = AsyncMock(return_value=1)

            mock_resolve.return_value = {1: "player1", 2: "player2"}

            response = client.get("/api/users/123/replays")

        assert response.status_code == 200
        data = response.json()
        assert len(data["replays"]) == 1
        assert data["total"] == 1
        assert data["replays"][0]["game_id"] == "ABC123"
        assert data["replays"][0]["speed"] == "standard"
        assert data["replays"][0]["winner"] == 1

    def test_get_user_replays_four_player_game(self, client: TestClient) -> None:
        """Test getting replays for 4-player games with correct slot assignment."""
        mock_user = MagicMock()
        mock_user.id = 123

        # User is player 3 in a 4-player game
        mock_entry = MagicMock()
        mock_entry.game_time = datetime.now(UTC)
        mock_entry.game_info = {
            "speed": "standard",
            "boardType": "four_player",
            "player": 3,  # User is player 3
            "winner": 1,
            "winReason": "last_standing",
            "gameId": "4PLAYER",
            "ticks": 3000,
            "opponents": ["u:100", "u:200", "u:300"],  # 3 opponents
        }

        with patch(
            "kfchess.api.users.UserRepository"
        ) as MockUserRepository, patch(
            "kfchess.db.repositories.user_game_history.UserGameHistoryRepository"
        ) as MockHistoryRepository, patch(
            "kfchess.api.users.resolve_player_names"
        ) as mock_resolve:
            mock_user_repo = MockUserRepository.return_value
            mock_user_repo.get_by_id = AsyncMock(return_value=mock_user)

            mock_history_repo = MockHistoryRepository.return_value
            mock_history_repo.list_by_user = AsyncMock(return_value=[mock_entry])
            mock_history_repo.count_by_user = AsyncMock(return_value=1)

            # Mock resolve_player_names to verify correct slot assignment
            # Should be called with: {3: "u:123", 1: "u:100", 2: "u:200", 4: "u:300"}
            def verify_players(db, players):
                assert 3 in players  # User's slot
                assert players[3] == "u:123"
                # Opponents should be in slots 1, 2, 4 (not 3)
                assert 1 in players
                assert 2 in players
                assert 4 in players
                return {k: f"player{k}" for k in players}

            mock_resolve.side_effect = verify_players

            response = client.get("/api/users/123/replays")

        assert response.status_code == 200
        data = response.json()
        assert len(data["replays"]) == 1
        assert data["replays"][0]["board_type"] == "four_player"
        # Verify all 4 players are in the response
        assert len(data["replays"][0]["players"]) == 4

    def test_get_user_replays_user_not_found(self, client: TestClient) -> None:
        """Test getting replays for non-existent user."""
        with patch(
            "kfchess.api.users.UserRepository"
        ) as MockUserRepository:
            mock_user_repo = MockUserRepository.return_value
            mock_user_repo.get_by_id = AsyncMock(return_value=None)

            response = client.get("/api/users/999999/replays")

        assert response.status_code == 404
        assert response.json()["detail"] == "User not found"

    def test_get_user_replays_pagination(self, client: TestClient) -> None:
        """Test pagination parameters are respected."""
        mock_user = MagicMock()
        mock_user.id = 123

        with patch(
            "kfchess.api.users.UserRepository"
        ) as MockUserRepository, patch(
            "kfchess.db.repositories.user_game_history.UserGameHistoryRepository"
        ) as MockHistoryRepository:
            mock_user_repo = MockUserRepository.return_value
            mock_user_repo.get_by_id = AsyncMock(return_value=mock_user)

            mock_history_repo = MockHistoryRepository.return_value
            mock_history_repo.list_by_user = AsyncMock(return_value=[])
            mock_history_repo.count_by_user = AsyncMock(return_value=25)

            response = client.get("/api/users/123/replays?limit=5&offset=10")

        assert response.status_code == 200
        # Verify list_by_user was called with correct params
        mock_history_repo.list_by_user.assert_called_once()
        call_args = mock_history_repo.list_by_user.call_args
        assert call_args[1]["limit"] == 5
        assert call_args[1]["offset"] == 10

    def test_get_user_replays_limit_validation(self, client: TestClient) -> None:
        """Test that limit is validated (1-50)."""
        mock_user = MagicMock()
        mock_user.id = 123

        with patch(
            "kfchess.api.users.UserRepository"
        ) as MockUserRepository:
            mock_user_repo = MockUserRepository.return_value
            mock_user_repo.get_by_id = AsyncMock(return_value=mock_user)

            # Test limit too high
            response = client.get("/api/users/123/replays?limit=100")
            assert response.status_code == 422  # Validation error

            # Test limit too low
            response = client.get("/api/users/123/replays?limit=0")
            assert response.status_code == 422  # Validation error
