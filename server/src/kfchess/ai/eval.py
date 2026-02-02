"""Evaluation function for scoring candidate moves."""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

from kfchess.ai.move_gen import CandidateMove, MoveCategory
from kfchess.ai.state_extractor import AIState
from kfchess.ai.tactics import PIECE_VALUES
from kfchess.game.pieces import PieceType

if TYPE_CHECKING:
    from kfchess.ai.arrival_field import ArrivalData

# Scoring weights for Level 1
MATERIAL_WEIGHT = 10.0
KING_DANGER_WEIGHT = 3.0
CENTER_CONTROL_WEIGHT = 1.0
DEVELOPMENT_WEIGHT = 0.8
PAWN_ADVANCE_WEIGHT = 0.5

# Level 2 weights
SAFETY_WEIGHT = 4.0
COMMITMENT_WEIGHT = 0.15
EVASION_WEIGHT = MATERIAL_WEIGHT  # Saving a piece ≈ capturing one of equal value

# Noise fractions by level
NOISE_SIGMA_BY_LEVEL: dict[int, float] = {
    1: 0.35,
    2: 0.17,
    3: 0.08,
}

# Backward compat
NOISE_SIGMA_FRACTION = 0.35


class Eval:
    """Scores candidate moves for AI selection."""

    @staticmethod
    def score_candidates(
        candidates: list[CandidateMove],
        ai_state: AIState,
        noise: bool = True,
        level: int = 1,
        arrival_data: ArrivalData | None = None,
    ) -> list[tuple[CandidateMove, float]]:
        """Score all candidate moves and return sorted (best first).

        Args:
            candidates: Moves to score
            ai_state: AI state snapshot
            noise: Whether to add Gaussian noise
            level: AI difficulty level (affects scoring terms)
            arrival_data: Arrival fields for margin-based scoring (L2+)

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
        tps = ai_state.speed_config.ticks_per_square if ai_state.speed_config else 30

        scored: list[tuple[CandidateMove, float]] = []
        for candidate in candidates:
            score = _score_move(
                candidate, ai_state, enemy_king_pos, own_king_pos,
                center_r, center_c, max_dist,
                level=level, arrival_data=arrival_data, tps=tps,
            )
            scored.append((candidate, score))

        # Add noise
        if noise and scored:
            scores = [s for _, s in scored]
            score_range = max(scores) - min(scores) if len(scores) > 1 else 1.0
            sigma_frac = NOISE_SIGMA_BY_LEVEL.get(level, 0.35)
            sigma = max(score_range * sigma_frac, 0.1)
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
    level: int = 1,
    arrival_data: ArrivalData | None = None,
    tps: int = 30,
) -> float:
    """Compute deterministic score for a move."""
    score = 0.0
    dest = (candidate.to_row, candidate.to_col)

    # Material: value of captured piece
    if candidate.category == MoveCategory.CAPTURE and candidate.capture_type:
        if arrival_data is not None:
            # Net exchange value accounting for recapture risk
            from kfchess.ai.tactics import capture_feasibility as _cap_feas
            exchange_value = _cap_feas(candidate, ai_state, arrival_data)
            score += exchange_value * MATERIAL_WEIGHT
        else:
            # Fallback: assume all captures are safe
            score += PIECE_VALUES.get(candidate.capture_type, 0) * MATERIAL_WEIGHT

    # Evasion bonus: scale by piece value (saving a queen >> saving a pawn)
    if candidate.category == MoveCategory.EVASION and candidate.ai_piece is not None:
        evading_value = PIECE_VALUES.get(candidate.ai_piece.piece.type, 1.0)
        score += evading_value * EVASION_WEIGHT

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
            if _is_on_back_rank(piece.grid_position, ai_state):
                score += DEVELOPMENT_WEIGHT

        # Pawn advancement: reward pawns moving toward promotion
        if piece.type == PieceType.PAWN:
            advancement = _pawn_advancement(
                candidate.to_row, candidate.to_col, ai_state,
            )
            score += advancement * PAWN_ADVANCE_WEIGHT * 0.1

        # Safety and commitment scoring
        if arrival_data is not None:
            from kfchess.ai.tactics import move_safety as _move_safety

            # Post-arrival safety: can enemy reach dest before our
            # cooldown expires? Positive = safe, negative = vulnerable.
            safety_ticks = _move_safety(candidate, arrival_data)
            # Normalize: scale ticks to ~[-5, 5] range
            safety_score = max(-5.0, min(5.0, safety_ticks / (tps * 2)))
            score += safety_score * SAFETY_WEIGHT

            # Commitment penalty: penalize long-distance moves
            from_pos = piece.grid_position
            travel_dist = _chebyshev_distance(from_pos, dest)
            commitment = travel_dist * COMMITMENT_WEIGHT
            score -= commitment

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


# Back rank positions per player. 2-player: row-based. 4-player: mixed.
_BACK_RANKS: dict[int, tuple[str, int]] = {
    1: ("row", 7),   # 2P: bottom row; 4P: uses col 11, handled by board_width check
    2: ("row", 0),   # 2P: top row; 4P: uses row 11
    3: ("col", 0),   # 4P only: left col
    4: ("row", 0),   # 4P only: top row
}


def _is_on_back_rank(
    pos: tuple[int, int], ai_state: AIState,
) -> bool:
    """Check if a piece is on its player's back rank."""
    player = ai_state.ai_player
    is_4p = ai_state.board_width > 8
    if is_4p:
        if player == 1:
            return pos[1] == 11  # East: col 11
        elif player == 2:
            return pos[0] == 11  # South: row 11
        elif player == 3:
            return pos[1] == 0   # West: col 0
        elif player == 4:
            return pos[0] == 0   # North: row 0
    else:
        if player == 1:
            return pos[0] == 7
        elif player == 2:
            return pos[0] == 0
    return False


def _pawn_advancement(
    to_row: int, to_col: int, ai_state: AIState,
) -> float:
    """Compute how advanced a pawn destination is (0 = home, higher = closer to promotion)."""
    player = ai_state.ai_player
    is_4p = ai_state.board_width > 8
    if is_4p:
        if player == 1:
            return 11 - to_col  # East→left: higher col = less advanced
        elif player == 2:
            return 11 - to_row  # South→up
        elif player == 3:
            return to_col        # West→right
        elif player == 4:
            return to_row        # North→down
    else:
        if player == 1:
            return 7 - to_row   # Bottom→up
        elif player == 2:
            return to_row        # Top→down
    return 0.0
