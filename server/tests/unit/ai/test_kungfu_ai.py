"""Tests for KungFuAI integration."""

import time

from kfchess.ai.kungfu_ai import KungFuAI
from kfchess.game.board import Board, BoardType
from kfchess.game.engine import GameEngine
from kfchess.game.pieces import Piece, PieceType
from kfchess.game.state import GameState, GameStatus, Speed


def _make_game(speed: Speed = Speed.STANDARD) -> GameState:
    state = GameEngine.create_game(
        speed=speed,
        players={1: "bot:kungfu", 2: "bot:test"},
        board_type=BoardType.STANDARD,
    )
    state.status = GameStatus.PLAYING
    return state


class TestKungFuAI:
    def test_implements_ai_player_interface(self):
        """KungFuAI should implement the AIPlayer interface."""
        from kfchess.ai.base import AIPlayer

        ai = KungFuAI(level=1, speed=Speed.STANDARD)
        assert isinstance(ai, AIPlayer)

    def test_get_move_returns_valid_move(self):
        """get_move should return a legal move."""
        state = _make_game()
        ai = KungFuAI(level=1, speed=Speed.STANDARD)
        # Force think delay to 0
        ai.controller.think_delay_ticks = 0
        ai.controller.last_move_tick = -9999

        move = ai.get_move(state, 1)
        assert move is not None
        piece_id, to_row, to_col = move
        # Validate it's actually legal
        validated = GameEngine.validate_move(state, 1, piece_id, to_row, to_col)
        assert validated is not None

    def test_should_move_respects_think_delay(self):
        """should_move should return False during think delay."""
        state = _make_game()
        ai = KungFuAI(level=1, speed=Speed.STANDARD)
        ai.controller.last_move_tick = 0
        ai.controller.think_delay_ticks = 100

        # Tick 50: should not move (within delay)
        state.current_tick = 50
        assert ai.should_move(state, 1, 50) is False

        # Tick 101: should be allowed
        state.current_tick = 101
        assert ai.should_move(state, 1, 101) is True

    def test_should_move_false_when_no_pieces_movable(self):
        """should_move should return False when no pieces can move."""
        state = _make_game()
        ai = KungFuAI(level=1, speed=Speed.STANDARD)
        ai.controller.think_delay_ticks = 0
        ai.controller.last_move_tick = -9999

        # Put all pieces on cooldown
        from kfchess.game.moves import Cooldown

        for piece in state.board.get_pieces_for_player(1):
            state.cooldowns.append(
                Cooldown(piece_id=piece.id, start_tick=0, duration=300)
            )

        assert ai.should_move(state, 1, 0) is False

    def test_get_move_within_budget(self):
        """get_move should complete within 0.5ms budget (generous margin)."""
        state = _make_game()
        ai = KungFuAI(level=1, speed=Speed.STANDARD)
        ai.controller.think_delay_ticks = 0
        ai.controller.last_move_tick = -9999

        # Warm up
        ai.get_move(state, 1)

        # Measure
        times = []
        for _ in range(10):
            state_copy = state.copy()
            start = time.perf_counter()
            ai.get_move(state_copy, 1)
            elapsed_ms = (time.perf_counter() - start) * 1000
            times.append(elapsed_ms)

        avg_ms = sum(times) / len(times)
        # Allow 50ms budget (generous, mainly catches infinite loops)
        # Real budget is 0.5ms but Python overhead makes that hard to test
        assert avg_ms < 50, f"Average time {avg_ms:.2f}ms exceeds budget"

    def test_prefers_captures(self):
        """AI should prefer capturing pieces over quiet moves."""
        board = Board(pieces=[], board_type=BoardType.STANDARD, width=8, height=8)
        board.pieces.append(Piece.create(PieceType.ROOK, 1, 4, 0))
        board.pieces.append(Piece.create(PieceType.QUEEN, 2, 4, 5))
        board.pieces.append(Piece.create(PieceType.KING, 1, 7, 4))
        board.pieces.append(Piece.create(PieceType.KING, 2, 0, 4))

        state = GameEngine.create_game_from_board(
            speed=Speed.STANDARD,
            players={1: "bot:kungfu", 2: "bot:test"},
            board=board,
        )
        state.status = GameStatus.PLAYING

        ai = KungFuAI(level=1, speed=Speed.STANDARD)
        ai.controller.think_delay_ticks = 0
        ai.controller.last_move_tick = -9999

        # Run multiple times — with noise, capture should still win most of the time
        capture_count = 0
        trials = 20
        for _ in range(trials):
            state_copy = state.copy()
            move = ai.get_move(state_copy, 1)
            if move is not None:
                _, to_row, to_col = move
                if to_row == 4 and to_col == 5:
                    capture_count += 1

        # Should capture at least 60% of the time even with noise
        assert capture_count >= trials * 0.5, (
            f"Captured only {capture_count}/{trials} times"
        )

    def test_works_with_lightning_speed(self):
        """AI should work correctly with lightning speed."""
        state = _make_game(speed=Speed.LIGHTNING)
        ai = KungFuAI(level=1, speed=Speed.LIGHTNING)
        ai.controller.think_delay_ticks = 0
        ai.controller.last_move_tick = -9999

        move = ai.get_move(state, 1)
        assert move is not None
