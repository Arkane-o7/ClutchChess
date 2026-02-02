"""Tactical filters for AI move validation.

Validates captures and positional moves using post-arrival safety
analysis, ensuring the AI accounts for cooldown vulnerability.
"""

from kfchess.ai.arrival_field import ArrivalData
from kfchess.ai.move_gen import CandidateMove, MoveCategory
from kfchess.ai.state_extractor import AIState
from kfchess.game.pieces import PieceType

# Discount on our piece loss when recapture is possible but not certain.
# 1.0 = assume recapture always happens, 0.0 = ignore recapture risk.
RECAPTURE_DISCOUNT = 0.8

# Piece values for exchange evaluation
PIECE_VALUES: dict[PieceType, float] = {
    PieceType.PAWN: 1.0,
    PieceType.KNIGHT: 3.0,
    PieceType.BISHOP: 3.0,
    PieceType.ROOK: 3.0,
    PieceType.QUEEN: 9.0,
    PieceType.KING: 100.0,
}


def compute_travel_ticks(
    from_row: int, from_col: int,
    to_row: int, to_col: int,
    piece_type: PieceType,
    tps: int,
) -> int:
    """Estimate travel time in ticks for a move.

    This is an approximation — the engine computes exact path length,
    but we use Chebyshev distance for sliders and fixed costs for knights.
    """
    if piece_type == PieceType.KNIGHT:
        return 2 * tps  # Knights always move 2 segments
    # Sliders, king, pawn: distance along the path
    dr = abs(to_row - from_row)
    dc = abs(to_col - from_col)
    dist = max(dr, dc)  # Chebyshev = path length for diagonal/straight
    return dist * tps


def capture_feasibility(
    candidate: CandidateMove,
    ai_state: AIState,
    arrival_data: ArrivalData,
) -> float:
    """Evaluate the net value of a capture.

    Returns the expected material gain in piece-value units:
    - Safe capture (no recapture): full captured piece value
    - Recapture likely: captured_value - our_value * RECAPTURE_DISCOUNT
      (discounted because the enemy might not actually recapture)

    Non-capture moves return 0.0.
    """
    if candidate.category != MoveCategory.CAPTURE:
        return 0.0

    dest = (candidate.to_row, candidate.to_col)
    capture_value = PIECE_VALUES.get(candidate.capture_type, 0) if candidate.capture_type else 0
    our_value = PIECE_VALUES.get(candidate.ai_piece.piece.type, 0) if candidate.ai_piece else 0

    # Find the captured piece ID for exclusion
    captured_piece_id: str | None = None
    if ai_state is not None:
        for ep in ai_state.get_enemy_pieces():
            if ep.piece.grid_position == dest:
                captured_piece_id = ep.piece.id
                break

    # Compute our travel time
    travel_ticks = arrival_data.tps  # Default 1 square
    if candidate.ai_piece is not None:
        from_pos = candidate.ai_piece.piece.grid_position
        travel_ticks = compute_travel_ticks(
            from_pos[0], from_pos[1],
            dest[0], dest[1],
            candidate.ai_piece.piece.type,
            arrival_data.tps,
        )

    # Post-arrival safety: can enemy recapture during our cooldown?
    safety = arrival_data.post_arrival_safety(
        dest[0], dest[1], travel_ticks,
        exclude_piece_id=captured_piece_id,
    )

    if safety >= 0:
        # No recapture possible — full value
        return capture_value

    # Enemy can recapture — net exchange with discount
    return capture_value - our_value * RECAPTURE_DISCOUNT


def move_safety(
    candidate: CandidateMove,
    arrival_data: ArrivalData,
) -> int:
    """Compute post-arrival safety for a non-capture move.

    Returns safety margin in ticks. Positive = safe (enemy can't
    reach destination before our cooldown expires).
    """
    dest = (candidate.to_row, candidate.to_col)

    travel_ticks = arrival_data.tps  # Default
    if candidate.ai_piece is not None:
        from_pos = candidate.ai_piece.piece.grid_position
        travel_ticks = compute_travel_ticks(
            from_pos[0], from_pos[1],
            dest[0], dest[1],
            candidate.ai_piece.piece.type,
            arrival_data.tps,
        )

    return arrival_data.post_arrival_safety(dest[0], dest[1], travel_ticks)
