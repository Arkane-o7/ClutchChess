
export class CollisionSystem {
    constructor(config) {
        this.radius = config.COLLISION_RADIUS;
    }

    check(pieces) {
        const destroyed = new Set();
        // Filter only moving, non-airborne pieces as initiators
        const movingPieces = pieces.filter(p => p.isMoving && !p.isAirborne);
        const threshold = this.radius * 2;
        const thresholdSq = threshold * threshold;

        for (const p1 of movingPieces) {
            // If initiator was already destroyed in a previous check this frame, skip
            if (destroyed.has(p1)) continue;

            for (const p2 of pieces) {
                // Self-collision check
                if (p1 === p2) continue;
                // Ignore already destroyed
                if (destroyed.has(p2)) continue;
                // Verify p2 is reachable (not airborne)
                if (p2.isAirborne) continue;

                // Distance Check
                const dx = p1.x - p2.x;
                const dy = p1.y - p2.y;
                const distSq = dx * dx + dy * dy;

                if (distSq < thresholdSq) {
                    // --- COLLISION EVENT ---
                    // "Hyper Chess" Rules:
                    // 1. Friendly Fire is ON (No team check).
                    // 2. Moving vs Moving = Crash (Both die).
                    // 3. Moving vs Static = Ram (Static dies, Moving continues).

                    if (p2.isMoving) {
                        // THE CRASH (Moving vs Moving)
                        // Both pieces explode.
                        destroyed.add(p1);
                        destroyed.add(p2);
                    } else {
                        // THE RAM (Moving vs Stationary)
                        // The stationary piece is destroyed. 
                        // The moving piece (p1) survives and continues (ICBM Gambit).
                        destroyed.add(p2);
                    }
                }
            }
        }

        return {
            destroyed: Array.from(destroyed),
            stopped: [] // No stopping, only death or glory.
        };
    }
}
