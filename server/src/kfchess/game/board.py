"""Board representation for Kung Fu Chess."""

from dataclasses import dataclass, field
from enum import Enum

from kfchess.game.pieces import Piece, PieceType


class BoardType(Enum):
    """Board layout type."""

    STANDARD = "standard"  # 8x8 standard chess
    FOUR_PLAYER = "four_player"  # 12x12 with corners cut


# Standard initial board setup
# Row 0: Black back row
# Row 1: Black pawns
# Row 6: White pawns
# Row 7: White back row
STANDARD_BACK_ROW = [
    PieceType.ROOK,
    PieceType.KNIGHT,
    PieceType.BISHOP,
    PieceType.QUEEN,
    PieceType.KING,
    PieceType.BISHOP,
    PieceType.KNIGHT,
    PieceType.ROOK,
]


@dataclass
class Board:
    """Chess board with pieces.

    Attributes:
        pieces: List of all pieces (including captured ones)
        board_type: Type of board layout
        width: Board width in squares
        height: Board height in squares
    """

    pieces: list[Piece] = field(default_factory=list)
    board_type: BoardType = BoardType.STANDARD
    width: int = 8
    height: int = 8

    @classmethod
    def create_standard(cls) -> "Board":
        """Create a standard 8x8 chess board with initial piece positions."""
        pieces: list[Piece] = []

        # Player 2 (black) back row - row 0
        for col, piece_type in enumerate(STANDARD_BACK_ROW):
            pieces.append(Piece.create(piece_type, player=2, row=0, col=col))

        # Player 2 (black) pawns - row 1
        for col in range(8):
            pieces.append(Piece.create(PieceType.PAWN, player=2, row=1, col=col))

        # Player 1 (white) pawns - row 6
        for col in range(8):
            pieces.append(Piece.create(PieceType.PAWN, player=1, row=6, col=col))

        # Player 1 (white) back row - row 7
        for col, piece_type in enumerate(STANDARD_BACK_ROW):
            pieces.append(Piece.create(piece_type, player=1, row=7, col=col))

        return cls(pieces=pieces, board_type=BoardType.STANDARD, width=8, height=8)

    @classmethod
    def create_empty(
        cls, board_type: BoardType = BoardType.STANDARD
    ) -> "Board":
        """Create an empty board (useful for tests and campaign levels)."""
        if board_type == BoardType.STANDARD:
            return cls(pieces=[], board_type=board_type, width=8, height=8)
        else:
            return cls(pieces=[], board_type=board_type, width=12, height=12)

    def copy(self) -> "Board":
        """Create a deep copy of the board."""
        return Board(
            pieces=[p.copy() for p in self.pieces],
            board_type=self.board_type,
            width=self.width,
            height=self.height,
        )

    def get_piece_by_id(self, piece_id: str) -> Piece | None:
        """Get a piece by its ID."""
        for piece in self.pieces:
            if piece.id == piece_id:
                return piece
        return None

    def get_piece_at(self, row: int, col: int) -> Piece | None:
        """Get an uncaptured piece at the given grid position.

        Uses grid position (rounded to nearest int) for matching.
        """
        for piece in self.pieces:
            if piece.captured:
                continue
            piece_row, piece_col = piece.grid_position
            if piece_row == row and piece_col == col:
                return piece
        return None

    def get_pieces_for_player(self, player: int) -> list[Piece]:
        """Get all uncaptured pieces for a player."""
        return [
            p for p in self.pieces if p.player == player and not p.captured
        ]

    def get_active_pieces(self) -> list[Piece]:
        """Get all uncaptured pieces."""
        return [p for p in self.pieces if not p.captured]

    def get_king(self, player: int) -> Piece | None:
        """Get the king piece for a player."""
        for piece in self.pieces:
            if piece.type == PieceType.KING and piece.player == player and not piece.captured:
                return piece
        return None

    def is_valid_square(self, row: int, col: int) -> bool:
        """Check if a square is valid on this board."""
        if row < 0 or row >= self.height or col < 0 or col >= self.width:
            return False

        if self.board_type == BoardType.FOUR_PLAYER:
            # 4-player board has corners cut off (2x2 in each corner)
            if row < 2 and col < 2:
                return False
            if row < 2 and col >= self.width - 2:
                return False
            if row >= self.height - 2 and col < 2:
                return False
            if row >= self.height - 2 and col >= self.width - 2:
                return False

        return True

    def add_piece(self, piece: Piece) -> None:
        """Add a piece to the board."""
        self.pieces.append(piece)

    def remove_piece(self, piece_id: str) -> bool:
        """Remove a piece from the board. Returns True if found and removed."""
        for i, piece in enumerate(self.pieces):
            if piece.id == piece_id:
                del self.pieces[i]
                return True
        return False
