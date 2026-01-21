"""Dummy AI that makes random valid moves.

This is used for testing gameplay mechanics with a simple opponent.
"""

import random

from kfchess.ai.base import AIPlayer
from kfchess.game.engine import GameEngine
from kfchess.game.state import GameState


class DummyAI(AIPlayer):
    """AI that makes random valid moves at random intervals."""

    def __init__(self, move_probability: float = 0.1):
        """Initialize the dummy AI.

        Args:
            move_probability: Probability of attempting a move each tick (0.0-1.0).
                             Default 0.1 means ~1 move per second at 10 ticks/sec.
        """
        self.move_probability = move_probability

    def should_move(self, state: GameState, player: int, current_tick: int) -> bool:
        """Randomly decide whether to move this tick."""
        # Always try to move if we haven't moved recently
        # Random chance to move based on probability
        return random.random() < self.move_probability

    def get_move(self, state: GameState, player: int) -> tuple[str, int, int] | None:
        """Return a random legal move."""
        legal_moves = GameEngine.get_legal_moves(state, player)
        if not legal_moves:
            return None

        # Pick a random move
        piece_id, to_row, to_col = random.choice(legal_moves)
        return (piece_id, to_row, to_col)
