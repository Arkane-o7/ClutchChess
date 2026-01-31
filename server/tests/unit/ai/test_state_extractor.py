"""Tests for StateExtractor."""


from kfchess.ai.state_extractor import AIState, PieceStatus, StateExtractor
from kfchess.game.board import BoardType
from kfchess.game.engine import GameEngine
from kfchess.game.moves import Cooldown
from kfchess.game.pieces import PieceType
from kfchess.game.state import GameState, GameStatus, Speed


def _make_game(speed: Speed = Speed.STANDARD) -> GameState:
    """Create a standard game in PLAYING state."""
    state = GameEngine.create_game(
        speed=speed,
        players={1: "bot:test1", 2: "bot:test2"},
        board_type=BoardType.STANDARD,
    )
    state.status = GameStatus.PLAYING
    return state


class TestStateExtractor:
    def test_extract_initial_board(self):
        """All pieces should be IDLE on initial board."""
        state = _make_game()
        ai_state = StateExtractor.extract(state, ai_player=1)

        assert isinstance(ai_state, AIState)
        assert ai_state.ai_player == 1
        assert ai_state.board_width == 8
        assert ai_state.board_height == 8

        # All 32 pieces should be present (none captured)
        assert len(ai_state.pieces) == 32

        # All should be idle
        for p in ai_state.pieces:
            assert p.status == PieceStatus.IDLE
            assert p.cooldown_remaining == 0
            assert p.destination is None
            assert p.travel_direction is None

    def test_movable_pieces_initial(self):
        """Player 1 should have 16 movable pieces initially."""
        state = _make_game()
        ai_state = StateExtractor.extract(state, ai_player=1)
        movable = ai_state.get_movable_pieces()
        # All 16 player 1 pieces are idle
        assert len(movable) == 16

    def test_traveling_piece_shows_destination_for_own(self):
        """AI's own traveling piece should have destination set."""
        state = _make_game()
        # Move a pawn
        move = GameEngine.validate_move(state, 1, "P:1:6:4", 5, 4)
        assert move is not None
        GameEngine.apply_move(state, move)

        ai_state = StateExtractor.extract(state, ai_player=1)
        pawn = next(p for p in ai_state.pieces if p.piece.id == "P:1:6:4")
        assert pawn.status == PieceStatus.TRAVELING
        assert pawn.destination == (5, 4)

    def test_traveling_piece_hides_destination_for_enemy(self):
        """Enemy traveling piece should show direction, not destination."""
        state = _make_game()
        # Move player 2's pawn
        move = GameEngine.validate_move(state, 2, "P:2:1:4", 2, 4)
        assert move is not None
        GameEngine.apply_move(state, move)

        # Extract from player 1's perspective
        ai_state = StateExtractor.extract(state, ai_player=1)
        pawn = next(p for p in ai_state.pieces if p.piece.id == "P:2:1:4")
        assert pawn.status == PieceStatus.TRAVELING
        assert pawn.destination is None
        assert pawn.travel_direction is not None
        # Moving from row 1 to row 2 = direction (1.0, 0.0)
        assert pawn.travel_direction == (1.0, 0.0)

    def test_cooldown_piece(self):
        """Piece on cooldown should have COOLDOWN status."""
        state = _make_game()
        state.cooldowns.append(Cooldown(piece_id="P:1:6:4", start_tick=0, duration=300))

        ai_state = StateExtractor.extract(state, ai_player=1)
        pawn = next(p for p in ai_state.pieces if p.piece.id == "P:1:6:4")
        assert pawn.status == PieceStatus.COOLDOWN
        assert pawn.cooldown_remaining == 300

    def test_enemy_king(self):
        """Should find enemy king."""
        state = _make_game()
        ai_state = StateExtractor.extract(state, ai_player=1)
        enemy_king = ai_state.get_enemy_king()
        assert enemy_king is not None
        assert enemy_king.piece.type == PieceType.KING
        assert enemy_king.piece.player == 2

    def test_own_king(self):
        """Should find own king."""
        state = _make_game()
        ai_state = StateExtractor.extract(state, ai_player=1)
        own_king = ai_state.get_own_king()
        assert own_king is not None
        assert own_king.piece.type == PieceType.KING
        assert own_king.piece.player == 1
