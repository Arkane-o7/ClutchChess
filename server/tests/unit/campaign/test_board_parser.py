"""Tests for campaign board parser."""

import pytest

from clutchchess.campaign.board_parser import PIECE_TYPE_MAP, parse_board_string
from clutchchess.game.board import BoardType
from clutchchess.game.pieces import PieceType


class TestParseBoardString:
    """Tests for parse_board_string function."""

    def test_parse_empty_8x8_board(self) -> None:
        """Test parsing an empty 8x8 board."""
        board_str = """
0000000000000000
0000000000000000
0000000000000000
0000000000000000
0000000000000000
0000000000000000
0000000000000000
0000000000000000
"""
        board = parse_board_string(board_str, BoardType.STANDARD)
        assert board.board_type == BoardType.STANDARD
        assert len(board.pieces) == 0
        assert board.width == 8
        assert board.height == 8

    def test_parse_simple_board_with_kings(self) -> None:
        """Test parsing board with king vs king."""
        board_str = """
00000000K2000000
0000000000000000
0000000000000000
0000000000000000
0000000000000000
0000000000000000
0000000000000000
00000000K1000000
"""
        board = parse_board_string(board_str, BoardType.STANDARD)
        assert len(board.pieces) == 2

        king1 = board.get_king(1)
        king2 = board.get_king(2)
        assert king1 is not None
        assert king2 is not None
        assert king1.grid_position == (7, 4)
        assert king2.grid_position == (0, 4)

    def test_parse_various_pieces(self) -> None:
        """Test parsing all piece types."""
        board_str = """
R2N2B2Q2K2B2N2R2
P2P2P2P2P2P2P2P2
0000000000000000
0000000000000000
0000000000000000
0000000000000000
P1P1P1P1P1P1P1P1
R1N1B1Q1K1B1N1R1
"""
        board = parse_board_string(board_str, BoardType.STANDARD)
        # 16 pieces per player = 32 total
        assert len(board.pieces) == 32

        # Verify player 1 pieces
        p1_pieces = board.get_pieces_for_player(1)
        assert len(p1_pieces) == 16
        p1_types = [p.type for p in p1_pieces]
        assert p1_types.count(PieceType.PAWN) == 8
        assert p1_types.count(PieceType.ROOK) == 2
        assert p1_types.count(PieceType.KNIGHT) == 2
        assert p1_types.count(PieceType.BISHOP) == 2
        assert p1_types.count(PieceType.QUEEN) == 1
        assert p1_types.count(PieceType.KING) == 1

    def test_parse_asymmetric_board(self) -> None:
        """Test parsing an asymmetric board (campaign level style)."""
        board_str = """
00000000K2000000
0000000000000000
0000000000000000
0000000000000000
0000000000000000
0000000000000000
P1P1P1P1P1P1P1P1
R1N1B1Q1K1B1N1R1
"""
        board = parse_board_string(board_str, BoardType.STANDARD)

        # Player 2 has only king
        p2_pieces = board.get_pieces_for_player(2)
        assert len(p2_pieces) == 1
        assert p2_pieces[0].type == PieceType.KING

        # Player 1 has full army
        p1_pieces = board.get_pieces_for_player(1)
        assert len(p1_pieces) == 16

    def test_parse_wrong_row_count_raises(self) -> None:
        """Test that wrong number of rows raises ValueError."""
        board_str = """
0000000000000000
0000000000000000
"""
        with pytest.raises(ValueError, match="Expected 8 rows"):
            parse_board_string(board_str, BoardType.STANDARD)

    def test_parse_wrong_column_count_raises(self) -> None:
        """Test that wrong column count raises ValueError."""
        board_str = """
00000000K2000000
0000000000000000
0000000000000000
0000000000000000
0000000000000000
0000000000000000
0000000000000000
00K100
"""
        with pytest.raises(ValueError, match="wrong length"):
            parse_board_string(board_str, BoardType.STANDARD)

    def test_parse_unknown_piece_type_raises(self) -> None:
        """Test that unknown piece type raises ValueError."""
        board_str = """
00000000X2000000
0000000000000000
0000000000000000
0000000000000000
0000000000000000
0000000000000000
0000000000000000
00000000K1000000
"""
        with pytest.raises(ValueError, match="Unknown piece type"):
            parse_board_string(board_str, BoardType.STANDARD)

    def test_parse_invalid_player_raises(self) -> None:
        """Test that invalid player number raises ValueError."""
        board_str = """
00000000KA000000
0000000000000000
0000000000000000
0000000000000000
0000000000000000
0000000000000000
0000000000000000
00000000K1000000
"""
        with pytest.raises(ValueError, match="Invalid player number"):
            parse_board_string(board_str, BoardType.STANDARD)

    def test_piece_type_map_completeness(self) -> None:
        """Verify all standard piece types are mapped."""
        assert "P" in PIECE_TYPE_MAP
        assert "N" in PIECE_TYPE_MAP
        assert "B" in PIECE_TYPE_MAP
        assert "R" in PIECE_TYPE_MAP
        assert "Q" in PIECE_TYPE_MAP
        assert "K" in PIECE_TYPE_MAP
        assert PIECE_TYPE_MAP["K"] == PieceType.KING
        assert PIECE_TYPE_MAP["P"] == PieceType.PAWN

    def test_parse_4player_board(self) -> None:
        """Test parsing a 12x12 4-player board."""
        # Minimal 4-player board with just kings
        # 12 columns × 2 chars = 24 chars per row
        board_str = """
000000K40000000000000000
000000000000000000000000
000000000000000000000000
000000000000000000000000
000000000000000000000000
K30000000000000000000000
0000000000000000000000K1
000000000000000000000000
000000000000000000000000
000000000000000000000000
000000000000000000000000
000000K20000000000000000
"""
        board = parse_board_string(board_str, BoardType.FOUR_PLAYER)
        assert board.board_type == BoardType.FOUR_PLAYER
        assert board.width == 12
        assert board.height == 12
        assert len(board.pieces) == 4

        # Verify all 4 kings exist
        for player in [1, 2, 3, 4]:
            king = board.get_king(player)
            assert king is not None, f"King for player {player} not found"
