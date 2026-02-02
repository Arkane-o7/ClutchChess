"""Tests for tactical filters."""

from kfchess.ai.arrival_field import ArrivalData, ArrivalField
from kfchess.ai.move_gen import CandidateMove, MoveCategory
from kfchess.ai.state_extractor import StateExtractor
from kfchess.ai.tactics import capture_feasibility, move_safety
from kfchess.game.board import BoardType
from kfchess.game.engine import GameEngine
from kfchess.game.pieces import PieceType
from kfchess.game.state import GameStatus, Speed


def _make_state(speed=Speed.STANDARD):
    state = GameEngine.create_game(
        speed=speed,
        players={1: "bot:ai1", 2: "bot:ai2"},
        board_type=BoardType.STANDARD,
    )
    state.status = GameStatus.PLAYING
    return state


class TestCaptureFeasibility:
    def test_capture_with_recapture_even_trade(self):
        """Capture where enemy can recapture, same piece value → small positive."""
        data = ArrivalData(
            our_time={(3, 3): 60},
            enemy_time={(3, 3): 0},  # Target is sitting there
            enemy_time_by_piece={
                "target": {(3, 3): 0},
            },
            tps=30,
            cd_ticks=300,
        )
        state = _make_state()
        ai_state = StateExtractor.extract(state, 1)

        pawn_piece = None
        for ap in ai_state.get_own_pieces():
            if ap.piece.type == PieceType.PAWN:
                pawn_piece = ap
                break

        candidate = CandidateMove(
            piece_id=pawn_piece.piece.id, to_row=3, to_col=3,
            category=MoveCategory.CAPTURE,
            capture_type=PieceType.PAWN,
            ai_piece=pawn_piece,
        )
        # ai_state=None → no exclusion → enemy_time=0, safety negative → recapture
        # Pawn(1) takes pawn(1): 1.0 - 1.0 * 0.8 = 0.2 (slightly positive)
        score = capture_feasibility(candidate, None, data)
        assert 0 < score < 1.0

    def test_safe_capture_with_exclusion(self):
        """After excluding captured piece, no recapture → feasibility 1.0."""
        data = ArrivalData(
            our_time={(3, 3): 30},
            enemy_time={(3, 3): 0},
            enemy_time_by_piece={
                "target_piece": {(3, 3): 0},
                # No other enemy piece can reach (3,3)
            },
            tps=30,
            cd_ticks=300,
        )
        # When ai_state has an enemy at (3,3) with id "target_piece",
        # capture_feasibility excludes it. Since pawn is at ~(6,x),
        # travel is ~3*30=90. After exclusion, enemy_time=INF.
        # safety = INF - (90+300) >> 0 → feasibility 1.0.
        # But our ai_state doesn't have an enemy at (3,3), so
        # captured_piece_id will be None. Test the exclusion logic directly:
        excl_time = data.get_enemy_time_excluding(3, 3, "target_piece")
        assert excl_time >= 999_999  # No other enemy can reach

    def test_losing_capture_enemy_can_recapture(self):
        """Sending queen to capture pawn on defended square → low score."""
        data = ArrivalData(
            our_time={(3, 3): 60},
            enemy_time={(3, 3): 0},
            enemy_time_by_piece={
                "target": {(3, 3): 0},
                "defender": {(3, 3): 30},  # Another enemy reaches in 30 ticks
            },
            tps=30,
            cd_ticks=300,
        )

        state = _make_state()
        ai_state = StateExtractor.extract(state, 1)
        queen = None
        for ap in ai_state.get_own_pieces():
            if ap.piece.type == PieceType.QUEEN:
                queen = ap
                break

        candidate = CandidateMove(
            piece_id=queen.piece.id, to_row=3, to_col=3,
            category=MoveCategory.CAPTURE,
            capture_type=PieceType.PAWN,
            ai_piece=queen,
        )
        score = capture_feasibility(candidate, None, data)
        # Queen (9) captures pawn (1), recapture: 1.0 - 9.0 * 0.8 = -6.2
        assert score < 0

    def test_non_capture_returns_zero(self):
        """Non-capture moves return 0.0 (no material gain)."""
        data = ArrivalData(tps=30, cd_ticks=300)
        candidate = CandidateMove(
            piece_id="p1_r1", to_row=3, to_col=3,
            category=MoveCategory.POSITIONAL,
        )
        assert capture_feasibility(candidate, None, data) == 0.0


class TestMoveSafety:
    def test_safe_move_near_home(self):
        """Moving near our back rank is safe — enemy is far."""
        state = _make_state()
        ai_state = StateExtractor.extract(state, 1)
        data = ArrivalField.compute(ai_state, state.config)

        pawn = None
        for ap in ai_state.get_own_pieces():
            if ap.piece.type == PieceType.PAWN:
                pawn = ap
                break

        candidate = CandidateMove(
            piece_id=pawn.piece.id, to_row=5, to_col=pawn.piece.grid_position[1],
            category=MoveCategory.POSITIONAL,
            ai_piece=pawn,
        )
        safety = move_safety(candidate, data)
        assert safety > 0  # Safe near our side

    def test_unsafe_move_deep_territory(self):
        """Moving deep into enemy territory is unsafe."""
        state = _make_state()
        ai_state = StateExtractor.extract(state, 1)
        data = ArrivalField.compute(ai_state, state.config)

        # Use a knight for a hypothetical long-range move
        knight = None
        for ap in ai_state.get_own_pieces():
            if ap.piece.type == PieceType.KNIGHT:
                knight = ap
                break

        candidate = CandidateMove(
            piece_id=knight.piece.id, to_row=2, to_col=4,
            category=MoveCategory.POSITIONAL,
            ai_piece=knight,
        )
        safety = move_safety(candidate, data)
        # Near enemy pieces with cooldown exposure — unsafe
        assert safety < 0
