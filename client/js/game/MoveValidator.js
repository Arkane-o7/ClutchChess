/**
 * Clutch Chess - Move Validator
 * Calculates legal moves for each piece type
 */

export class MoveValidator {
    constructor(config) {
        this.config = config;
        this.tileSize = config.TILE_SIZE;
    }

    getValidMoves(piece, allPieces) {
        const moves = [];
        const col = Math.floor(piece.x / this.tileSize);
        const row = Math.floor(piece.y / this.tileSize);

        switch (piece.type) {
            case 'p':
                this.getPawnMoves(piece, col, row, allPieces, moves);
                break;
            case 'r':
                this.getSlidingMoves(col, row, [[0, 1], [0, -1], [1, 0], [-1, 0]], allPieces, piece.isWhite, moves);
                break;
            case 'n':
                this.getKnightMoves(col, row, allPieces, piece.isWhite, moves);
                break;
            case 'b':
                this.getSlidingMoves(col, row, [[1, 1], [1, -1], [-1, 1], [-1, -1]], allPieces, piece.isWhite, moves);
                break;
            case 'q':
                this.getSlidingMoves(col, row, [[0, 1], [0, -1], [1, 0], [-1, 0], [1, 1], [1, -1], [-1, 1], [-1, -1]], allPieces, piece.isWhite, moves);
                break;
            case 'k':
                this.getKingMoves(col, row, allPieces, piece.isWhite, moves);
                break;
        }

        return moves;
    }

    getPawnMoves(piece, col, row, allPieces, moves) {
        const dir = piece.isWhite ? -1 : 1;
        const startRow = piece.isWhite ? 6 : 1;

        // Forward 1
        if (this.isValidSquare(col, row + dir)) {
            // Standard chess: Pawn can't move forward if blocked. 
            // We keep this rule for target selection to avoid "telefrag ability" on simple moves, 
            // although physics would resolve it as a collision.
            const blocker = this.getPieceAt(col, row + dir, allPieces);
            if (!blocker) {
                moves.push({ col, row: row + dir, isAttack: false });

                // Forward 2 from start
                if (row === startRow) {
                    const blocker2 = this.getPieceAt(col, row + dir * 2, allPieces);
                    if (!blocker2) {
                        moves.push({ col, row: row + dir * 2, isAttack: false });
                    }
                }
            }
        }

        // Diagonal attacks - ALWAYS POSSIBLE in Hyper Chess
        [-1, 1].forEach(dc => {
            const newCol = col + dc;
            const newRow = row + dir;
            if (this.isValidSquare(newCol, newRow)) {
                moves.push({ col: newCol, row: newRow, isAttack: true });
            }
        });
    }

    getSlidingMoves(col, row, directions, allPieces, isWhite, moves) {
        directions.forEach(([dc, dr]) => {
            let c = col + dc;
            let r = row + dr;

            while (this.isValidSquare(c, r)) {
                // In Hyper Chess, pieces don't block path selection.
                // You can target any square in the line.
                // Physics will handle what happens if you hit something on the way.

                // We mark it as 'isAttack' if there's an enemy there just for UI feedback,
                // but strictly speaking any move is valid.
                const target = this.getPieceAt(c, r, allPieces);
                const isAttack = target && target.isWhite !== isWhite;

                // Optional: Prevent landing explicitly on own pieces?
                // Spec says "Standard chess movement rules apply for target selection".
                // In standard chess, you cannot move to a square occupied by a friendly piece.
                if (!target || target.isWhite !== isWhite) {
                    moves.push({ col: c, row: r, isAttack });
                }

                c += dc;
                r += dr;
            }
        });
    }

    getKnightMoves(col, row, allPieces, isWhite, moves) {
        const offsets = [
            [1, 2], [1, -2], [-1, 2], [-1, -2],
            [2, 1], [2, -1], [-2, 1], [-2, -1]
        ];

        offsets.forEach(([dc, dr]) => {
            const c = col + dc;
            const r = row + dr;
            if (this.isValidSquare(c, r)) {
                const target = this.getPieceAt(c, r, allPieces);
                // Allow attacking friendly pieces
                const isAttack = !!target;
                moves.push({ col: c, row: r, isAttack });
            }
        });
    }

    getKingMoves(col, row, allPieces, isWhite, moves) {
        const offsets = [
            [0, 1], [0, -1], [1, 0], [-1, 0],
            [1, 1], [1, -1], [-1, 1], [-1, -1]
        ];

        offsets.forEach(([dc, dr]) => {
            const c = col + dc;
            const r = row + dr;
            if (this.isValidSquare(c, r)) {
                const target = this.getPieceAt(c, r, allPieces);
                // Allow attacking friendly pieces
                const isAttack = !!target;
                moves.push({ col: c, row: r, isAttack });
            }
        });
    }

    isValidSquare(col, row) {
        return col >= 0 && col < 8 && row >= 0 && row < 8;
    }

    getPieceAt(col, row, allPieces) {
        return allPieces.find(p => {
            if (p.isMoving) return false;
            const pCol = Math.floor(p.x / this.tileSize);
            const pRow = Math.floor(p.y / this.tileSize);
            return pCol === col && pRow === row;
        });
    }
}
