"""Tests for the ELO rating system."""

import pytest

from kfchess.game.elo import (
    DEFAULT_RATING,
    HIGH_RATING_THRESHOLD,
    K_FACTOR,
    K_FACTOR_HIGH,
    MIN_RATING,
    RatingChange,
    UserRatingStats,
    calculate_expected_score,
    clamp_rating,
    get_belt,
    get_k_factor,
    get_rating_key,
    parse_rating_key,
    update_ratings_2p,
    update_ratings_4p,
)


class TestConstants:
    """Test that constants have expected values."""

    def test_default_rating(self):
        assert DEFAULT_RATING == 1200

    def test_min_rating(self):
        assert MIN_RATING == 100

    def test_k_factor(self):
        assert K_FACTOR == 32

    def test_k_factor_high(self):
        assert K_FACTOR_HIGH == 16

    def test_high_rating_threshold(self):
        assert HIGH_RATING_THRESHOLD == 2000


class TestRatingChange:
    """Tests for RatingChange dataclass."""

    def test_belt_changed_true(self):
        """Belt changed should be True when belts differ."""
        change = RatingChange(
            old_rating=1090,
            new_rating=1110,
            old_belt="yellow",
            new_belt="green",
        )
        assert change.belt_changed is True

    def test_belt_changed_false(self):
        """Belt changed should be False when belts are same."""
        change = RatingChange(
            old_rating=1200,
            new_rating=1215,
            old_belt="green",
            new_belt="green",
        )
        assert change.belt_changed is False


class TestUserRatingStats:
    """Tests for UserRatingStats dataclass."""

    def test_default(self):
        """Default stats should have default rating and zero counts."""
        stats = UserRatingStats.default()
        assert stats.rating == DEFAULT_RATING
        assert stats.games == 0
        assert stats.wins == 0


class TestGetBelt:
    """Tests for belt determination."""

    def test_none_for_null_rating(self):
        """None rating should return 'none' belt."""
        assert get_belt(None) == "none"

    def test_white_belt(self):
        """Ratings 0-899 should be white belt."""
        assert get_belt(0) == "white"
        assert get_belt(100) == "white"
        assert get_belt(899) == "white"

    def test_yellow_belt(self):
        """Ratings 900-1099 should be yellow belt."""
        assert get_belt(900) == "yellow"
        assert get_belt(1000) == "yellow"
        assert get_belt(1099) == "yellow"

    def test_green_belt(self):
        """Ratings 1100-1299 should be green belt."""
        assert get_belt(1100) == "green"
        assert get_belt(1200) == "green"
        assert get_belt(1299) == "green"

    def test_purple_belt(self):
        """Ratings 1300-1499 should be purple belt."""
        assert get_belt(1300) == "purple"
        assert get_belt(1400) == "purple"
        assert get_belt(1499) == "purple"

    def test_orange_belt(self):
        """Ratings 1500-1699 should be orange belt."""
        assert get_belt(1500) == "orange"
        assert get_belt(1600) == "orange"
        assert get_belt(1699) == "orange"

    def test_blue_belt(self):
        """Ratings 1700-1899 should be blue belt."""
        assert get_belt(1700) == "blue"
        assert get_belt(1800) == "blue"
        assert get_belt(1899) == "blue"

    def test_brown_belt(self):
        """Ratings 1900-2099 should be brown belt."""
        assert get_belt(1900) == "brown"
        assert get_belt(2000) == "brown"
        assert get_belt(2099) == "brown"

    def test_red_belt(self):
        """Ratings 2100-2299 should be red belt."""
        assert get_belt(2100) == "red"
        assert get_belt(2200) == "red"
        assert get_belt(2299) == "red"

    def test_black_belt(self):
        """Ratings 2300+ should be black belt."""
        assert get_belt(2300) == "black"
        assert get_belt(2500) == "black"
        assert get_belt(3000) == "black"

    def test_belt_boundaries(self):
        """Test exact boundary values."""
        # Each belt starts at its threshold
        assert get_belt(899) == "white"
        assert get_belt(900) == "yellow"
        assert get_belt(1099) == "yellow"
        assert get_belt(1100) == "green"
        assert get_belt(2299) == "red"
        assert get_belt(2300) == "black"


class TestGetKFactor:
    """Tests for K-factor determination."""

    def test_low_rating_uses_normal_k(self):
        """Ratings below threshold should use normal K-factor."""
        assert get_k_factor(1000) == K_FACTOR
        assert get_k_factor(1500) == K_FACTOR
        assert get_k_factor(1999) == K_FACTOR

    def test_high_rating_uses_reduced_k(self):
        """Ratings at or above threshold should use reduced K-factor."""
        assert get_k_factor(2000) == K_FACTOR_HIGH
        assert get_k_factor(2500) == K_FACTOR_HIGH


class TestClampRating:
    """Tests for rating clamping."""

    def test_rating_above_min_unchanged(self):
        """Ratings above minimum should be unchanged."""
        assert clamp_rating(1200) == 1200
        assert clamp_rating(MIN_RATING) == MIN_RATING
        assert clamp_rating(MIN_RATING + 1) == MIN_RATING + 1

    def test_rating_below_min_clamped(self):
        """Ratings below minimum should be clamped to minimum."""
        assert clamp_rating(0) == MIN_RATING
        assert clamp_rating(50) == MIN_RATING
        assert clamp_rating(-100) == MIN_RATING


class TestCalculateExpectedScore:
    """Tests for expected score calculation."""

    def test_equal_ratings(self):
        """Equal ratings should give 0.5 expected score."""
        expected = calculate_expected_score(1200, 1200)
        assert expected == pytest.approx(0.5)

    def test_higher_rating_higher_expected(self):
        """Higher rated player should have higher expected score."""
        expected = calculate_expected_score(1400, 1200)
        assert expected > 0.5
        assert expected == pytest.approx(0.759, abs=0.001)

    def test_lower_rating_lower_expected(self):
        """Lower rated player should have lower expected score."""
        expected = calculate_expected_score(1200, 1400)
        assert expected < 0.5
        assert expected == pytest.approx(0.241, abs=0.001)

    def test_expected_scores_sum_to_one(self):
        """Expected scores of two players should sum to 1."""
        ea = calculate_expected_score(1300, 1500)
        eb = calculate_expected_score(1500, 1300)
        assert ea + eb == pytest.approx(1.0)

    def test_400_point_difference(self):
        """400 point difference should give ~0.91 expected score."""
        expected = calculate_expected_score(1600, 1200)
        assert expected == pytest.approx(0.909, abs=0.001)


class TestUpdateRatings2P:
    """Tests for 2-player rating updates."""

    def test_player_a_wins(self):
        """Test rating update when player A wins."""
        new_a, new_b = update_ratings_2p(1200, 1200, winner=1)
        # Winner gains, loser loses
        assert new_a > 1200
        assert new_b < 1200
        # Changes should be symmetric for equal ratings
        assert new_a - 1200 == 1200 - new_b

    def test_player_b_wins(self):
        """Test rating update when player B wins."""
        new_a, new_b = update_ratings_2p(1200, 1200, winner=2)
        assert new_a < 1200
        assert new_b > 1200

    def test_draw(self):
        """Test rating update on draw with equal ratings."""
        new_a, new_b = update_ratings_2p(1200, 1200, winner=0)
        # Equal ratings, draw = no change
        assert new_a == 1200
        assert new_b == 1200

    def test_upset_gives_larger_change(self):
        """Lower rated player winning should give larger rating change."""
        # Favorite wins
        new_a_fav, new_b_fav = update_ratings_2p(1400, 1200, winner=1)
        # Underdog wins
        new_a_upset, new_b_upset = update_ratings_2p(1400, 1200, winner=2)

        # Upset should cause larger change
        favorite_gain = new_a_fav - 1400
        underdog_gain = new_b_upset - 1200
        assert underdog_gain > abs(favorite_gain)

    def test_high_rating_uses_reduced_k(self):
        """Player above 2000 should have smaller rating changes."""
        # High rated player
        new_high, new_low = update_ratings_2p(2100, 1200, winner=2)
        # Lower rated player beating high rated
        high_loss = 2100 - new_high

        # Normal K player
        new_normal_a, new_normal_b = update_ratings_2p(1800, 1200, winner=2)
        normal_loss = 1800 - new_normal_a

        # High rated player should lose less due to K_FACTOR_HIGH
        # (even though expected was higher, K is lower)
        # This is a bit tricky to test exactly, but K_HIGH = 16 vs K = 32
        assert high_loss < normal_loss * 0.7  # Should be roughly half

    def test_rating_floor(self):
        """Rating should not go below MIN_RATING."""
        new_a, new_b = update_ratings_2p(MIN_RATING, 2000, winner=2)
        assert new_a >= MIN_RATING

    def test_rating_calculation_example(self):
        """Test specific rating calculation matches expected."""
        # 1200 vs 1200, player 1 wins
        # Expected = 0.5, Actual = 1.0
        # Change = K * (1.0 - 0.5) = 32 * 0.5 = 16
        new_a, new_b = update_ratings_2p(1200, 1200, winner=1)
        assert new_a == 1216
        assert new_b == 1184


class TestUpdateRatings4P:
    """Tests for 4-player rating updates."""

    def test_winner_gains_rating(self):
        """Winner should gain rating."""
        ratings = {1: 1200, 2: 1200, 3: 1200, 4: 1200}
        new_ratings = update_ratings_4p(ratings, winner=1)
        assert new_ratings[1] > 1200

    def test_others_lose_to_winner(self):
        """Non-winners should lose rating to winner."""
        ratings = {1: 1200, 2: 1200, 3: 1200, 4: 1200}
        new_ratings = update_ratings_4p(ratings, winner=1)
        # Losers all lose (since they "lost" to winner)
        assert new_ratings[2] < 1200
        assert new_ratings[3] < 1200
        assert new_ratings[4] < 1200

    def test_non_winner_non_losers_draw(self):
        """Non-winners who didn't play each other are treated as draws."""
        ratings = {1: 1200, 2: 1200, 3: 1200, 4: 1200}
        new_ratings = update_ratings_4p(ratings, winner=1)
        # Players 2, 3, 4 all drew against each other (neither won)
        # So their changes are from: 1 loss to winner, 2 draws
        # With equal ratings, draws don't change rating
        # So all losers should have same rating
        assert new_ratings[2] == new_ratings[3] == new_ratings[4]

    def test_draw_no_change(self):
        """Draw with equal ratings should give no change."""
        ratings = {1: 1200, 2: 1200, 3: 1200, 4: 1200}
        new_ratings = update_ratings_4p(ratings, winner=0)
        assert new_ratings[1] == 1200
        assert new_ratings[2] == 1200
        assert new_ratings[3] == 1200
        assert new_ratings[4] == 1200

    def test_different_ratings(self):
        """Test with different starting ratings."""
        ratings = {1: 1400, 2: 1200, 3: 1000, 4: 1200}
        new_ratings = update_ratings_4p(ratings, winner=3)

        # Underdog (player 3, 1000) beating favorites should gain a lot
        assert new_ratings[3] > 1000
        # Top player (1400) losing to underdog should lose a lot
        assert new_ratings[1] < 1400

    def test_rating_sum_conservation_approx(self):
        """Total rating change should approximately sum to zero."""
        ratings = {1: 1200, 2: 1300, 3: 1400, 4: 1100}
        new_ratings = update_ratings_4p(ratings, winner=2)

        old_sum = sum(ratings.values())
        new_sum = sum(new_ratings.values())
        # Due to rounding, might not be exactly equal
        # But should be close (within a few points)
        assert abs(new_sum - old_sum) <= 4  # At most 1 point per player from rounding

    def test_high_rated_player_smaller_k(self):
        """Player over 2000 should have smaller K-factor."""
        ratings = {1: 2100, 2: 1200, 3: 1200, 4: 1200}
        new_ratings = update_ratings_4p(ratings, winner=2)

        # Player 1 (2100) loses but uses K_FACTOR_HIGH = 16
        high_rated_loss = ratings[1] - new_ratings[1]

        # Compare to what would happen with normal K
        # This is approximate - high rated player should lose less
        # than a 1900 player would in same situation
        ratings_normal = {1: 1900, 2: 1200, 3: 1200, 4: 1200}
        new_normal = update_ratings_4p(ratings_normal, winner=2)
        normal_loss = ratings_normal[1] - new_normal[1]

        # High rated (K=16) should lose about half what normal (K=32) does
        assert high_rated_loss < normal_loss

    def test_rating_floor_4p(self):
        """Rating should not go below MIN_RATING in 4p games."""
        ratings = {1: MIN_RATING, 2: 2000, 3: 2000, 4: 2000}
        new_ratings = update_ratings_4p(ratings, winner=2)
        assert new_ratings[1] >= MIN_RATING


class TestRatingKey:
    """Tests for rating key generation and parsing."""

    def test_get_rating_key_2p_standard(self):
        assert get_rating_key(2, "standard") == "2p_standard"

    def test_get_rating_key_2p_lightning(self):
        assert get_rating_key(2, "lightning") == "2p_lightning"

    def test_get_rating_key_4p_standard(self):
        assert get_rating_key(4, "standard") == "4p_standard"

    def test_get_rating_key_4p_lightning(self):
        assert get_rating_key(4, "lightning") == "4p_lightning"

    def test_parse_rating_key_2p_standard(self):
        player_count, speed = parse_rating_key("2p_standard")
        assert player_count == 2
        assert speed == "standard"

    def test_parse_rating_key_4p_lightning(self):
        player_count, speed = parse_rating_key("4p_lightning")
        assert player_count == 4
        assert speed == "lightning"

    def test_roundtrip(self):
        """get_rating_key and parse_rating_key should be inverses."""
        for player_count in [2, 4]:
            for speed in ["standard", "lightning"]:
                key = get_rating_key(player_count, speed)
                parsed_count, parsed_speed = parse_rating_key(key)
                assert parsed_count == player_count
                assert parsed_speed == speed
