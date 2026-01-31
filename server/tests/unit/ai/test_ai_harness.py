"""AI-vs-AI test harness: KungFuAI Level 1 vs DummyAI."""

import pytest

from kfchess.ai.dummy import DummyAI
from kfchess.ai.kungfu_ai import KungFuAI
from kfchess.game.board import BoardType
from kfchess.game.engine import GameEngine
from kfchess.game.state import GameStatus, Speed


def run_ai_game(
    ai1,
    ai2,
    speed: Speed = Speed.STANDARD,
    max_ticks: int = 30000,
) -> int | None:
    """Run a game between two AIs.

    Returns:
        1 if AI1 wins, 2 if AI2 wins, 0 for draw, None if max ticks reached
    """
    state = GameEngine.create_game(
        speed=speed,
        players={1: "bot:ai1", 2: "bot:ai2"},
        board_type=BoardType.STANDARD,
    )
    state.status = GameStatus.PLAYING

    for _tick in range(max_ticks):
        # AI 1 moves
        if ai1.should_move(state, 1, state.current_tick):
            move_data = ai1.get_move(state, 1)
            if move_data:
                piece_id, to_row, to_col = move_data
                move = GameEngine.validate_move(state, 1, piece_id, to_row, to_col)
                if move:
                    GameEngine.apply_move(state, move)

        # AI 2 moves
        if ai2.should_move(state, 2, state.current_tick):
            move_data = ai2.get_move(state, 2)
            if move_data:
                piece_id, to_row, to_col = move_data
                move = GameEngine.validate_move(state, 2, piece_id, to_row, to_col)
                if move:
                    GameEngine.apply_move(state, move)

        # Tick
        GameEngine.tick(state)

        if state.is_finished:
            return state.winner

    return None  # Max ticks reached


class TestAIHarness:
    @pytest.mark.slow
    def test_kungfu_beats_dummy(self):
        """KungFuAI Level 1 should beat DummyAI consistently."""
        wins = 0
        losses = 0
        draws = 0
        incomplete = 0
        num_games = 10

        for _i in range(num_games):
            kungfu = KungFuAI(level=1, speed=Speed.STANDARD)
            dummy = DummyAI(speed=Speed.STANDARD)
            # Force KungFuAI to move quickly for testing
            kungfu.controller.think_delay_ticks = 0
            kungfu.controller.last_move_tick = -9999

            result = run_ai_game(kungfu, dummy, max_ticks=20000)
            if result == 1:
                wins += 1
            elif result == 2:
                losses += 1
            elif result == 0:
                draws += 1
            else:
                incomplete += 1

        # KungFuAI should win more than it loses
        assert wins > losses, (
            f"KungFuAI won {wins}, lost {losses}, drew {draws}, "
            f"incomplete {incomplete} out of {num_games} games"
        )

    @pytest.mark.slow
    def test_kungfu_vs_dummy_lightning(self):
        """KungFuAI should also beat DummyAI in lightning speed."""
        wins = 0
        losses = 0
        num_games = 5

        for _i in range(num_games):
            kungfu = KungFuAI(level=1, speed=Speed.LIGHTNING)
            dummy = DummyAI(speed=Speed.LIGHTNING)
            kungfu.controller.think_delay_ticks = 0
            kungfu.controller.last_move_tick = -9999

            result = run_ai_game(kungfu, dummy, speed=Speed.LIGHTNING, max_ticks=30000)
            if result == 1:
                wins += 1
            elif result == 2:
                losses += 1

        assert wins >= losses, (
            f"KungFuAI won {wins}, lost {losses} out of {num_games} lightning games"
        )
