"""Candidate move generation for AI."""

from __future__ import annotations

import random
from enum import Enum
from typing import TYPE_CHECKING

from kfchess.ai.state_extractor import AIPiece, AIState, PieceStatus
from kfchess.game.engine import GameEngine
from kfchess.game.pieces import PieceType
from kfchess.game.state import GameState

if TYPE_CHECKING:
    from kfchess.ai.arrival_field import ArrivalData



class MoveCategory(Enum):
    """Category of a candidate move, used for prioritization."""

    CAPTURE = "capture"
    EVASION = "evasion"
    KING_THREAT = "king_threat"
    POSITIONAL = "positional"


class CandidateMove:
    """A candidate move with metadata for scoring."""

    __slots__ = ("piece_id", "to_row", "to_col", "category", "capture_type", "ai_piece")

    def __init__(
        self,
        piece_id: str,
        to_row: int,
        to_col: int,
        category: MoveCategory,
        capture_type: PieceType | None = None,
        ai_piece: AIPiece | None = None,
    ):
        self.piece_id = piece_id
        self.to_row = to_row
        self.to_col = to_col
        self.category = category
        self.capture_type = capture_type
        self.ai_piece = ai_piece


class MoveGen:
    """Generates candidate moves for AI evaluation."""

    @staticmethod
    def generate_candidates(
        state: GameState,
        ai_state: AIState,
        ai_player: int,
        max_pieces: int = 2,
        max_candidates_per_piece: int = 4,
        level: int = 1,
        arrival_data: ArrivalData | None = None,
    ) -> list[CandidateMove]:
        """Generate candidate moves for AI.

        Picks up to max_pieces random movable pieces and generates
        up to max_candidates_per_piece for each.

        Args:
            state: Game state for move validation
            ai_state: AI-friendly state
            ai_player: Player number
            max_pieces: Max pieces to consider
            max_candidates_per_piece: Max candidates per piece
            level: AI difficulty level (affects pruning/evasion)
            arrival_data: Arrival fields for margin-based decisions (L2+)

        Returns:
            List of candidate moves
        """
        movable = ai_state.get_movable_pieces()
        if not movable:
            return []

        enemy_king = ai_state.get_enemy_king()
        enemy_king_pos = (
            enemy_king.piece.grid_position if enemy_king else None
        )

        # Build occupancy map for enemy pieces (for capture detection)
        enemy_positions: dict[tuple[int, int], PieceType] = {}
        for ep in ai_state.get_enemy_pieces():
            if ep.status != PieceStatus.TRAVELING:
                enemy_positions[ep.piece.grid_position] = ep.piece.type

        # Get all legal moves once (avoid per-piece brute-force scan)
        all_legal = GameEngine.get_legal_moves_fast(state, ai_player)

        # Group by piece_id
        moves_by_piece: dict[str, list[tuple[int, int]]] = {}
        for piece_id, to_row, to_col in all_legal:
            moves_by_piece.setdefault(piece_id, []).append((to_row, to_col))

        # Prioritize threatened pieces for evasion
        shuffled = list(movable)
        if arrival_data is not None:
            # Sort: threatened pieces first, then shuffle within groups
            threatened = []
            safe = []
            for p in shuffled:
                pos = p.piece.grid_position
                if arrival_data.is_piece_at_risk(pos[0], pos[1], p.cooldown_remaining):
                    threatened.append(p)
                else:
                    safe.append(p)
            random.shuffle(threatened)
            random.shuffle(safe)
            shuffled = threatened + safe
        else:
            random.shuffle(shuffled)

        candidates: list[CandidateMove] = []
        pieces_used = 0

        for ai_piece in shuffled:
            if pieces_used >= max_pieces and candidates:
                break

            piece_moves = moves_by_piece.get(ai_piece.piece.id)
            if not piece_moves:
                continue

            pieces_used += 1
            piece_candidates = _categorize_moves(
                ai_piece, piece_moves, enemy_positions, enemy_king_pos,
                level=level, arrival_data=arrival_data,
            )
            # Prioritize: captures, evasions, king threats, positional
            piece_candidates.sort(key=lambda c: _category_priority(c.category))
            candidates.extend(piece_candidates[:max_candidates_per_piece])

        return candidates


def _category_priority(cat: MoveCategory) -> int:
    """Lower = higher priority."""
    if cat == MoveCategory.CAPTURE:
        return 0
    if cat == MoveCategory.EVASION:
        return 1
    if cat == MoveCategory.KING_THREAT:
        return 2
    return 3


def _categorize_moves(
    ai_piece: AIPiece,
    moves: list[tuple[int, int]],
    enemy_positions: dict[tuple[int, int], PieceType],
    enemy_king_pos: tuple[int, int] | None,
    level: int = 1,
    arrival_data: ArrivalData | None = None,
) -> list[CandidateMove]:
    """Categorize pre-validated legal moves for a piece."""
    piece_id = ai_piece.piece.id
    candidates: list[CandidateMove] = []

    # Check if this piece is threatened
    piece_threatened = False
    if arrival_data is not None:
        pos = ai_piece.piece.grid_position
        piece_threatened = arrival_data.is_piece_at_risk(pos[0], pos[1], ai_piece.cooldown_remaining)

    for to_row, to_col in moves:
        dest = (to_row, to_col)

        # Compute travel time and safety for pruning/evasion
        travel = 0
        safety = 0
        if arrival_data is not None:
            from kfchess.ai.tactics import compute_travel_ticks
            travel = compute_travel_ticks(
                ai_piece.piece.grid_position[0],
                ai_piece.piece.grid_position[1],
                to_row, to_col,
                ai_piece.piece.type,
                arrival_data.tps,
            )
            safety = arrival_data.post_arrival_safety(to_row, to_col, travel)
            # Prune very unsafe non-capture moves
            if dest not in enemy_positions and safety < -(arrival_data.cd_ticks // 2):
                continue

        if dest in enemy_positions:
            candidates.append(
                CandidateMove(
                    piece_id=piece_id,
                    to_row=to_row,
                    to_col=to_col,
                    category=MoveCategory.CAPTURE,
                    capture_type=enemy_positions[dest],
                    ai_piece=ai_piece,
                )
            )
        elif piece_threatened and arrival_data is not None:
            # Threatened piece: categorize safe destinations as evasions
            cat = MoveCategory.EVASION if safety >= 0 else MoveCategory.POSITIONAL
            if enemy_king_pos and _is_king_threat(dest, enemy_king_pos):
                cat = MoveCategory.EVASION  # Evade toward enemy king = bonus
            candidates.append(
                CandidateMove(
                    piece_id=piece_id,
                    to_row=to_row,
                    to_col=to_col,
                    category=cat,
                    ai_piece=ai_piece,
                )
            )
        elif enemy_king_pos and _is_king_threat(dest, enemy_king_pos):
            candidates.append(
                CandidateMove(
                    piece_id=piece_id,
                    to_row=to_row,
                    to_col=to_col,
                    category=MoveCategory.KING_THREAT,
                    ai_piece=ai_piece,
                )
            )
        else:
            candidates.append(
                CandidateMove(
                    piece_id=piece_id,
                    to_row=to_row,
                    to_col=to_col,
                    category=MoveCategory.POSITIONAL,
                    ai_piece=ai_piece,
                )
            )

    return candidates


def _is_king_threat(dest: tuple[int, int], king_pos: tuple[int, int]) -> bool:
    """Check if destination is within 2 squares of the enemy king."""
    dr = abs(dest[0] - king_pos[0])
    dc = abs(dest[1] - king_pos[1])
    return dr <= 2 and dc <= 2
