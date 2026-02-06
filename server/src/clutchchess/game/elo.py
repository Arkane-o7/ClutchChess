"""ELO rating system for Clutch Chess.

This module provides ELO rating calculations for 2-player and 4-player games,
along with a belt ranking system based on rating thresholds.
"""

import math
from dataclasses import dataclass

DEFAULT_RATING = 1200
MIN_RATING = 100  # Floor to prevent discouraging new players
K_FACTOR = 32
K_FACTOR_HIGH = 16  # Used for ratings above HIGH_RATING_THRESHOLD
HIGH_RATING_THRESHOLD = 2000

# Belt thresholds (rating, belt_name) - ordered highest to lowest
BELT_THRESHOLDS = [
    (2300, "black"),
    (2100, "red"),
    (1900, "brown"),
    (1700, "blue"),
    (1500, "orange"),
    (1300, "purple"),
    (1100, "green"),
    (900, "yellow"),
    (0, "white"),
]


@dataclass
class RatingChange:
    """Result of a rating update for a single player."""

    old_rating: int
    new_rating: int
    old_belt: str
    new_belt: str
    belt_changed: bool = False

    def __post_init__(self) -> None:
        self.belt_changed = self.old_belt != self.new_belt


@dataclass
class UserRatingStats:
    """User's rating stats for a specific mode."""

    rating: int
    games: int
    wins: int

    @classmethod
    def default(cls) -> "UserRatingStats":
        return cls(rating=DEFAULT_RATING, games=0, wins=0)


def get_belt(rating: int | None) -> str:
    """Get belt name for a given rating. Returns 'none' for unranked."""
    if rating is None:
        return "none"
    for threshold, belt in BELT_THRESHOLDS:
        if rating >= threshold:
            return belt
    return "white"


def get_k_factor(rating: int) -> int:
    """Get K-factor based on rating. Lower K at high ratings for stability."""
    return K_FACTOR_HIGH if rating >= HIGH_RATING_THRESHOLD else K_FACTOR


def clamp_rating(rating: int) -> int:
    """Ensure rating doesn't fall below minimum."""
    return max(MIN_RATING, rating)


def calculate_expected_score(rating_a: int, rating_b: int) -> float:
    """Calculate expected score for player A against player B."""
    return 1.0 / (1 + math.pow(10, (rating_b - rating_a) / 400.0))


def update_ratings_2p(
    rating_a: int,
    rating_b: int,
    winner: int,  # 0=draw, 1=player A won, 2=player B won
) -> tuple[int, int]:
    """Calculate new ratings for a 2-player game.

    Args:
        rating_a: Current rating for player A (player 1)
        rating_b: Current rating for player B (player 2)
        winner: 0=draw, 1=player A won, 2=player B won

    Returns:
        Tuple of (new_rating_a, new_rating_b)
    """
    ea = calculate_expected_score(rating_a, rating_b)
    eb = 1.0 - ea

    if winner == 0:  # Draw
        sa, sb = 0.5, 0.5
    elif winner == 1:  # Player A won
        sa, sb = 1.0, 0.0
    else:  # Player B won
        sa, sb = 0.0, 1.0

    # Use dynamic K-factor based on each player's rating
    k_a = get_k_factor(rating_a)
    k_b = get_k_factor(rating_b)

    new_a = clamp_rating(int(round(rating_a + k_a * (sa - ea))))
    new_b = clamp_rating(int(round(rating_b + k_b * (sb - eb))))

    return new_a, new_b


def update_ratings_4p(
    ratings: dict[int, int],  # {player_num: rating}
    winner: int,  # 0=draw, 1-4=winner
) -> dict[int, int]:
    """Calculate new ratings for a 4-player game.

    Each player's rating change is calculated based on their performance
    against all opponents.

    Design note: When two players both lose to a third player, they are
    treated as having drawn against each other (actual=0.5). This is a
    simplification - a more complex system could track elimination order
    to give partial credit for lasting longer. The current approach is
    simpler and commonly used in multi-player ELO variants.

    Args:
        ratings: Dict mapping player_num to current rating
        winner: 0=draw, 1-4=winner player number

    Returns:
        Dict mapping player_num to new rating
    """
    new_ratings = {}
    players = list(ratings.keys())

    for player in players:
        total_change = 0.0
        my_rating = ratings[player]
        k = get_k_factor(my_rating)

        for opponent in players:
            if opponent == player:
                continue

            opp_rating = ratings[opponent]
            expected = calculate_expected_score(my_rating, opp_rating)

            # Determine actual score against this opponent
            if winner == 0:  # Draw
                actual = 0.5
            elif winner == player:  # I won
                actual = 1.0
            elif winner == opponent:  # This opponent won
                actual = 0.0
            else:  # Neither of us won - treated as draw
                actual = 0.5

            total_change += k * (actual - expected)

        # Average the change across all opponents
        avg_change = total_change / (len(players) - 1)
        new_ratings[player] = clamp_rating(int(round(my_rating + avg_change)))

    return new_ratings


def get_rating_key(player_count: int, speed: str) -> str:
    """Get the rating key for a game mode.

    Args:
        player_count: Number of players (2 or 4)
        speed: Game speed ("standard" or "lightning")

    Returns:
        Rating key like "2p_standard" or "4p_lightning"
    """
    prefix = "2p" if player_count == 2 else "4p"
    return f"{prefix}_{speed}"


def parse_rating_key(key: str) -> tuple[int, str]:
    """Parse a rating key into player_count and speed.

    Args:
        key: Rating key like "2p_standard"

    Returns:
        Tuple of (player_count, speed)
    """
    prefix, speed = key.split("_", 1)
    player_count = 2 if prefix == "2p" else 4
    return player_count, speed
