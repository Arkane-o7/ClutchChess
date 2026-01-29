/**
 * Clutch Chess - AI Controller
 * Simple aggressive AI for practice mode
 */

export class AIController {
    constructor(moveValidator, config) {
        this.moveValidator = moveValidator;
        this.config = config;
        this.cooldown = 0;
    }

    reset() {
        this.cooldown = 1;
    }

    getMove(pieces, aiColor, mana, dt) {
        // Gate: Check cooldown and mana
        this.cooldown -= dt;
        if (this.cooldown > 0) return null;
        if (mana < this.config.MANA_COST_PER_MOVE) return null;

        const isWhite = aiColor === 'white';
        // Candidate Selection: !isWhite AND !isMoving
        // (Assuming aiColor is 'black' for this spec, but keeping it generic)
        const candidates = pieces.filter(p => p.isWhite === isWhite && !p.isMoving);
        const enemies = pieces.filter(p => p.isWhite !== isWhite);

        if (candidates.length === 0) return null;

        // 1. Aggressive Heuristic: Greedy Kill
        for (const piece of candidates) {
            const moves = this.moveValidator.getValidMoves(piece, pieces);

            for (const move of moves) {
                const targetX = move.col * this.config.TILE_SIZE + this.config.TILE_SIZE / 2;
                const targetY = move.row * this.config.TILE_SIZE + this.config.TILE_SIZE / 2;

                // Check if TargetTile contains a White piece (Collision radius check)
                const hasTarget = enemies.some(enemy => {
                    const dx = enemy.x - targetX;
                    const dy = enemy.y - targetY;
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    return dist < (this.config.COLLISION_RADIUS * 2);
                });

                if (hasTarget) {
                    // Executing move immediately
                    this.setCooldown();
                    return { piece, target: move };
                }
            }
        }

        // 2. Random Heuristic
        const randomPiece = candidates[Math.floor(Math.random() * candidates.length)];
        const moves = this.moveValidator.getValidMoves(randomPiece, pieces);

        if (moves.length > 0) {
            const randomMove = moves[Math.floor(Math.random() * moves.length)];
            this.setCooldown();
            return { piece: randomPiece, target: randomMove };
        }

        return null;
    }

    setCooldown() {
        // Sets Random Cooldown (0.5s + Math.random())
        this.cooldown = 0.5 + Math.random();
    }
}
