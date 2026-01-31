"""Tests for Eval scoring function."""


from kfchess.ai.eval import Eval
from kfchess.ai.move_gen import CandidateMove, MoveCategory
from kfchess.ai.state_extractor import StateExtractor
from kfchess.game.board import Board, BoardType
from kfchess.game.engine import GameEngine
from kfchess.game.pieces import Piece, PieceType
from kfchess.game.state import GameStatus, Speed


def _make_simple_board() -> tuple:
    """Create a simple board with capture opportunities."""
    board = Board(pieces=[], board_type=BoardType.STANDARD, width=8, height=8)
    board.pieces.append(Piece.create(PieceType.ROOK, 1, 4, 0))
    board.pieces.append(Piece.create(PieceType.PAWN, 2, 4, 5))
    board.pieces.append(Piece.create(PieceType.QUEEN, 2, 4, 7))
    board.pieces.append(Piece.create(PieceType.KING, 1, 7, 4))
    board.pieces.append(Piece.create(PieceType.KING, 2, 0, 4))

    state = GameEngine.create_game_from_board(
        speed=Speed.STANDARD,
        players={1: "bot:test1", 2: "bot:test2"},
        board=board,
    )
    state.status = GameStatus.PLAYING
    ai_state = StateExtractor.extract(state, ai_player=1)
    return state, ai_state


class TestEval:
    def test_capture_queen_scores_higher_than_pawn(self):
        """Capturing a queen should score higher than capturing a pawn."""
        _, ai_state = _make_simple_board()
        rook_piece = ai_state.pieces_by_id["R:1:4:0"]

        capture_pawn = CandidateMove(
            "R:1:4:0", 4, 5, MoveCategory.CAPTURE, PieceType.PAWN, rook_piece
        )
        capture_queen = CandidateMove(
            "R:1:4:0", 4, 7, MoveCategory.CAPTURE, PieceType.QUEEN, rook_piece
        )
        quiet_move = CandidateMove(
            "R:1:4:0", 4, 3, MoveCategory.POSITIONAL, ai_piece=rook_piece
        )

        scored = Eval.score_candidates(
            [capture_pawn, capture_queen, quiet_move], ai_state, noise=False
        )

        # Queen capture should be first
        assert scored[0][0].capture_type == PieceType.QUEEN
        # Pawn capture should be second
        assert scored[1][0].capture_type == PieceType.PAWN
        # Quiet move last
        assert scored[2][0].category == MoveCategory.POSITIONAL

    def test_captures_beat_quiet_moves(self):
        """Any capture should score higher than a quiet move."""
        _, ai_state = _make_simple_board()
        rook_piece = ai_state.pieces_by_id["R:1:4:0"]

        capture = CandidateMove(
            "R:1:4:0", 4, 5, MoveCategory.CAPTURE, PieceType.PAWN, rook_piece
        )
        quiet = CandidateMove(
            "R:1:4:0", 3, 0, MoveCategory.POSITIONAL, ai_piece=rook_piece
        )

        scored = Eval.score_candidates([capture, quiet], ai_state, noise=False)
        assert scored[0][0].category == MoveCategory.CAPTURE

    def test_noise_can_change_ordering(self):
        """With noise, ordering may differ between runs (statistical test)."""
        _, ai_state = _make_simple_board()

        # Two moves with similar scores
        move_a = CandidateMove("R:1:4:0", 4, 3, MoveCategory.POSITIONAL)
        move_b = CandidateMove("R:1:4:0", 4, 2, MoveCategory.POSITIONAL)

        # Run many times and check if ordering ever changes
        orderings = set()
        for _ in range(50):
            scored = Eval.score_candidates([move_a, move_b], ai_state, noise=True)
            first_col = scored[0][0].to_col
            orderings.add(first_col)

        # With noise, we should see both orderings at least once
        assert len(orderings) > 1

    def test_center_preference(self):
        """Moves toward center should score higher than edge moves (no noise)."""
        state = GameEngine.create_game(
            speed=Speed.STANDARD,
            players={1: "bot:test1", 2: "bot:test2"},
            board_type=BoardType.STANDARD,
        )
        state.status = GameStatus.PLAYING
        ai_state = StateExtractor.extract(state, ai_player=1)
        knight_piece = ai_state.pieces_by_id["N:1:7:1"]

        # Knight to center vs knight to edge
        center_move = CandidateMove(
            "N:1:7:1", 5, 2, MoveCategory.POSITIONAL, ai_piece=knight_piece
        )
        edge_move = CandidateMove(
            "N:1:7:1", 5, 0, MoveCategory.POSITIONAL, ai_piece=knight_piece
        )

        scored = Eval.score_candidates(
            [center_move, edge_move], ai_state, noise=False
        )
        # Center move should score higher
        assert scored[0][0].to_col == 2
