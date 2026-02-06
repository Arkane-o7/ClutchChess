"""Unit tests for leaderboard API endpoints."""

from clutchchess.api.leaderboard import (
    VALID_MODES,
    LeaderboardEntry,
    LeaderboardResponse,
)


class TestLeaderboardModels:
    """Tests for leaderboard data models."""

    def test_valid_modes_contains_all_combinations(self):
        """Valid modes should include all 2p/4p and standard/lightning combos."""
        assert "2p_standard" in VALID_MODES
        assert "2p_lightning" in VALID_MODES
        assert "4p_standard" in VALID_MODES
        assert "4p_lightning" in VALID_MODES
        assert len(VALID_MODES) == 4

    def test_leaderboard_entry_fields(self):
        """LeaderboardEntry should have all required fields."""
        entry = LeaderboardEntry(
            rank=1,
            user_id=123,
            username="TestUser",
            picture_url=None,
            rating=1500,
            belt="orange",
            games_played=50,
            wins=30,
        )
        assert entry.rank == 1
        assert entry.user_id == 123
        assert entry.username == "TestUser"
        assert entry.rating == 1500
        assert entry.belt == "orange"
        assert entry.games_played == 50
        assert entry.wins == 30

    def test_leaderboard_response_fields(self):
        """LeaderboardResponse should have all required fields."""
        response = LeaderboardResponse(
            mode="2p_standard",
            entries=[],
        )
        assert response.mode == "2p_standard"
        assert response.entries == []


class TestLeaderboardModeValidation:
    """Tests for mode validation patterns."""

    def test_valid_2p_standard_mode(self):
        """2p_standard should be a valid mode."""
        assert "2p_standard" in VALID_MODES

    def test_valid_2p_lightning_mode(self):
        """2p_lightning should be a valid mode."""
        assert "2p_lightning" in VALID_MODES

    def test_valid_4p_standard_mode(self):
        """4p_standard should be a valid mode."""
        assert "4p_standard" in VALID_MODES

    def test_valid_4p_lightning_mode(self):
        """4p_lightning should be a valid mode."""
        assert "4p_lightning" in VALID_MODES
