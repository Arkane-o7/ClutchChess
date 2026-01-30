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
        // Standard rule: Pawns are blocked by physical presence directly in front
        if (this.isValidSquare(col, row + dir)) {
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

        // Diagonal attacks - "The Missile" / "Turbo Charge"
        // Always available as targets. 
        [-1, 1].forEach(dc => {
            const newCol = col + dc;
            const newRow = row + dir;
            if (this.isValidSquare(newCol, newRow)) {
                // Visual feedback only
                const target = this.getPieceAt(newCol, newRow, allPieces);
                const isAttack = !!target;

                moves.push({ col: newCol, row: newRow, isAttack });
            }
        });
    }

    getSlidingMoves(col, row, directions, allPieces, isWhite, moves) {
        directions.forEach(([dc, dr]) => {
            let c = col + dc;
            let r = row + dr;

            while (this.isValidSquare(c, r)) {
                // Hyper Chess Logic:
                // "Pieces... slide across the board... you can move a piece into the path... friendly fire... ICBM Gambit"
                // This implies you can target ANY square in the line, regardless of obstacles.
                // The physics engine handles collisions (Rams/Crashes) during transit.

                const target = this.getPieceAt(c, r, allPieces);
                const isAttack = !!target; // Visual indicator

                moves.push({ col: c, row: r, isAttack });

                // DO NOT BREAK. 
                // We allow targeting "through" pieces to set up rams/crashes.

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
