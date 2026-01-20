"""Tests for piece definitions."""

import pytest

from kfchess.game.pieces import Piece, PieceType


class TestPieceType:
    """Tests for the PieceType enum."""

    def test_piece_type_values(self):
        """Test piece type string values."""
        assert PieceType.PAWN.value == "P"
        assert PieceType.KNIGHT.value == "N"
        assert PieceType.BISHOP.value == "B"
        assert PieceType.ROOK.value == "R"
        assert PieceType.QUEEN.value == "Q"
        assert PieceType.KING.value == "K"

    def test_piece_type_str(self):
        """Test piece type string conversion."""
        assert str(PieceType.PAWN) == "P"
        assert str(PieceType.KING) == "K"


class TestPiece:
    """Tests for the Piece class."""

    def test_create_piece(self):
        """Test creating a piece with auto-generated ID."""
        piece = Piece.create(PieceType.PAWN, player=1, row=6, col=4)

        assert piece.type == PieceType.PAWN
        assert piece.player == 1
        assert piece.row == 6.0
        assert piece.col == 4.0
        assert piece.id == "P:1:6:4"
        assert piece.captured is False
        assert piece.moved is False

    def test_piece_position(self):
        """Test piece position properties."""
        piece = Piece.create(PieceType.KNIGHT, player=2, row=0, col=1)

        assert piece.position == (0.0, 1.0)
        assert piece.grid_position == (0, 1)

    def test_piece_position_interpolation(self):
        """Test grid position rounding during interpolation."""
        piece = Piece(
            id="P:1:6:4",
            type=PieceType.PAWN,
            player=1,
            row=5.6,  # Interpolated position
            col=4.0,
        )

        # Position should be exact
        assert piece.position == (5.6, 4.0)
        # Grid position should round
        assert piece.grid_position == (6, 4)

        # Test rounding at 0.5
        piece.row = 5.5
        assert piece.grid_position == (6, 4)  # Rounds to 6

        piece.row = 5.4
        assert piece.grid_position == (5, 4)  # Rounds to 5

    def test_piece_copy(self):
        """Test copying a piece."""
        original = Piece.create(PieceType.ROOK, player=1, row=7, col=0)
        original.moved = True
        original.captured = True

        copy = original.copy()

        # Should have same values
        assert copy.id == original.id
        assert copy.type == original.type
        assert copy.player == original.player
        assert copy.row == original.row
        assert copy.col == original.col
        assert copy.moved == original.moved
        assert copy.captured == original.captured

        # Should be independent
        copy.row = 5.0
        assert original.row == 7.0

    def test_piece_types(self):
        """Test creating all piece types."""
        for piece_type in PieceType:
            piece = Piece.create(piece_type, player=1, row=0, col=0)
            assert piece.type == piece_type
            assert piece.id.startswith(piece_type.value)
