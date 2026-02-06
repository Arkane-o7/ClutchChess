"""Board string parser for campaign levels."""

from clutchchess.game.board import Board, BoardType
from clutchchess.game.pieces import Piece, PieceType

PIECE_TYPE_MAP = {
    "P": PieceType.PAWN,
    "N": PieceType.KNIGHT,
    "B": PieceType.BISHOP,
    "R": PieceType.ROOK,
    "Q": PieceType.QUEEN,
    "K": PieceType.KING,
}


def parse_board_string(board_str: str, board_type: BoardType) -> Board:
    """Parse legacy board string format into a Board object.

    Board string format:
        - 8 rows for standard (8x8), 12 rows for 4-player (12x12)
        - Each square = 2 characters: piece type + player number
        - "00" = empty square
        - Piece types: P (pawn), N (knight), B (bishop), R (rook), Q (queen), K (king)
        - Players: 1-2 for standard, 1-4 for 4-player

    Args:
        board_str: Multi-line string with 2 chars per square
        board_type: Target board dimensions

    Returns:
        Board object with pieces placed

    Raises:
        ValueError: If the board string format is invalid
    """
    lines = [line.strip() for line in board_str.strip().splitlines() if line.strip()]

    if board_type == BoardType.STANDARD:
        expected_rows = 8
        expected_cols = 8
    else:
        expected_rows = 12
        expected_cols = 12

    if len(lines) != expected_rows:
        raise ValueError(f"Expected {expected_rows} rows, got {len(lines)}")

    board = Board.create_empty(board_type)

    for row, line in enumerate(lines):
        if len(line) != expected_cols * 2:
            raise ValueError(
                f"Row {row} has wrong length: {len(line)}, expected {expected_cols * 2}"
            )

        for col in range(expected_cols):
            cell = line[col * 2 : col * 2 + 2]
            if cell == "00":
                continue

            piece_type_char = cell[0]
            player_char = cell[1]

            if piece_type_char not in PIECE_TYPE_MAP:
                raise ValueError(f"Unknown piece type: {piece_type_char}")

            try:
                player = int(player_char)
            except ValueError:
                raise ValueError(f"Invalid player number: {player_char}") from None

            board.add_piece(
                Piece.create(
                    PIECE_TYPE_MAP[piece_type_char],
                    player=player,
                    row=row,
                    col=col,
                )
            )

    return board
