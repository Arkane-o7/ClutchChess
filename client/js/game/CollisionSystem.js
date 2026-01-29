
export class CollisionSystem {
    constructor(config) {
        this.radius = config.COLLISION_RADIUS;
    }

    check(pieces) {
        const destroyed = new Set();
        const movingPieces = pieces.filter(p => p.isMoving && !p.isAirborne);
        const threshold = this.radius * 2;
        const thresholdSq = threshold * threshold;

        // Optimization: Only check moving pieces against others
        // Complexity: O(M * N) where M = moving, N = total

        for (const p1 of movingPieces) {
            if (destroyed.has(p1)) continue;

            for (const p2 of pieces) {
                if (p1 === p2) continue;
                if (destroyed.has(p2)) continue;
                if (p2.isAirborne) continue;

                // Distance check
                const dx = p1.x - p2.x;
                const dy = p1.y - p2.y;
                const distSq = dx * dx + dy * dy;

                if (distSq < thresholdSq) {
                    // Collision Detected

                    if (p2.isMoving) {
                        // Moving vs Moving (Head-on)
                        // Both get destroyed
                        destroyed.add(p1);
                        destroyed.add(p2);
                    } else {
                        // Moving (p1) vs Static (p2)
                        // Static gets destroyed
                        destroyed.add(p2);
                    }
                }
            }
        }

        return {
            destroyed: Array.from(destroyed),
            stopped: []
        };
    }
}
