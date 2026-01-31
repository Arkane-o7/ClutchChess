"""Evaluation function for scoring candidate moves."""

import math
import random

from kfchess.ai.move_gen import CandidateMove, MoveCategory
from kfchess.ai.state_extractor import AIState
from kfchess.game.pieces import PieceType

# Material values
PIECE_VALUES: dict[PieceType, float] = {
    PieceType.PAWN: 1.0,
    PieceType.KNIGHT: 3.0,
    PieceType.BISHOP: 3.0,
    PieceType.ROOK: 5.0,
    PieceType.QUEEN: 9.0,
    PieceType.KING: 100.0,
}

# Scoring weights for Level 1
MATERIAL_WEIGHT = 10.0
KING_DANGER_WEIGHT = 3.0
CENTER_CONTROL_WEIGHT = 1.0
DEVELOPMENT_WEIGHT = 0.8
PAWN_ADVANCE_WEIGHT = 0.5

# Noise for Level 1 (30-40% of score range)
NOISE_SIGMA_FRACTION = 0.35


class Eval:
    """Scores candidate moves for AI selection."""

    @staticmethod
    def score_candidates(
        candidates: list[CandidateMove],
        ai_state: AIState,
        noise: bool = True,
    ) -> list[tuple[CandidateMove, float]]:
        """Score all candidate moves and return sorted (best first).

        Args:
            candidates: Moves to score
            ai_state: AI state snapshot
            noise: Whether to add Gaussian noise (Level 1 imperfection)

        Returns:
            List of (move, score) sorted by score descending
        """
        if not candidates:
            return []

        enemy_king = ai_state.get_enemy_king()
        enemy_king_pos = enemy_king.piece.grid_position if enemy_king else None
        own_king = ai_state.get_own_king()
        own_king_pos = own_king.piece.grid_position if own_king else None

        center_r = ai_state.board_height / 2.0
        center_c = ai_state.board_width / 2.0
        max_dist = _euclidean_distance((0, 0), (center_r, center_c))

        scored: list[tuple[CandidateMove, float]] = []
        for candidate in candidates:
            score = _score_move(
                candidate, ai_state, enemy_king_pos, own_king_pos,
                center_r, center_c, max_dist,
            )
            scored.append((candidate, score))

        # Add noise
        if noise and scored:
            scores = [s for _, s in scored]
            score_range = max(scores) - min(scores) if len(scores) > 1 else 1.0
            sigma = max(score_range * NOISE_SIGMA_FRACTION, 0.1)
            scored = [
                (m, s + random.gauss(0, sigma))
                for m, s in scored
            ]

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored


def _score_move(
    candidate: CandidateMove,
    ai_state: AIState,
    enemy_king_pos: tuple[int, int] | None,
    own_king_pos: tuple[int, int] | None,
    center_r: float,
    center_c: float,
    max_dist: float,
) -> float:
    """Compute deterministic score for a move."""
    score = 0.0
    dest = (candidate.to_row, candidate.to_col)

    # Material: value of captured piece
    if candidate.category == MoveCategory.CAPTURE and candidate.capture_type:
        score += PIECE_VALUES.get(candidate.capture_type, 0) * MATERIAL_WEIGHT

    # King danger: bonus for approaching enemy king
    if enemy_king_pos:
        dist = _chebyshev_distance(dest, enemy_king_pos)
        if dist <= 1:
            score += 5.0 * KING_DANGER_WEIGHT
        elif dist <= 3:
            score += (4.0 - dist) * KING_DANGER_WEIGHT

    # Use ai_piece directly (O(1) instead of O(n) search)
    ai_piece = candidate.ai_piece
    if ai_piece is not None:
        piece = ai_piece.piece

        # Own king safety: penalty for moving defenders away
        if own_king_pos:
            current_dist = _chebyshev_distance(piece.grid_position, own_king_pos)
            new_dist = _chebyshev_distance(dest, own_king_pos)
            if current_dist <= 2 and new_dist > current_dist:
                score -= 1.0
            if piece.type == PieceType.KING:
                dist_to_center = _euclidean_distance(dest, (center_r, center_c))
                if dist_to_center < 2.0:
                    score -= 2.0  # Don't rush king to center

        # Development: bonus for moving minor pieces off back rank
        if piece.type in (PieceType.KNIGHT, PieceType.BISHOP):
            from_row = piece.grid_position[0]
            if ai_state.ai_player == 1 and from_row == 7:
                score += DEVELOPMENT_WEIGHT
            elif ai_state.ai_player == 2 and from_row == 0:
                score += DEVELOPMENT_WEIGHT

        # Pawn advancement
        if piece.type == PieceType.PAWN:
            if ai_state.ai_player == 1:
                advancement = 7 - candidate.to_row
            else:
                advancement = candidate.to_row
            score += advancement * PAWN_ADVANCE_WEIGHT * 0.1

    # Center control
    dist_to_center = _euclidean_distance(dest, (center_r, center_c))
    center_bonus = (1.0 - dist_to_center / max_dist) * CENTER_CONTROL_WEIGHT
    score += center_bonus

    return score


def _chebyshev_distance(
    a: tuple[int, int] | tuple[float, float],
    b: tuple[int, int] | tuple[float, float],
) -> float:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def _euclidean_distance(
    a: tuple[int, int] | tuple[float, float],
    b: tuple[int, int] | tuple[float, float],
) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)
