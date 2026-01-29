/**
 * Clutch Chess - Matchmaker
 * Manages the matchmaking queue and creates matches
 */

export class MatchMaker {
    constructor() {
        this.queue = new Map(); // id -> { socket, joinTime, rating }
    }

    addToQueue(id, socket, userData) {
        this.queue.set(id, {
            socket,
            joinTime: Date.now(),
            rating: userData.rating,
            data: userData
        });
    }

    removeFromQueue(id) {
        this.queue.delete(id);
    }

    getQueueSize() {
        return this.queue.size;
    }

    tryMatch() {
        if (this.queue.size < 2) return null;

        // Simple FIFO matching
        // Could be enhanced with ELO-based matching
        const players = Array.from(this.queue.entries());

        if (players.length >= 2) {
            const [id1, player1] = players[0];
            const [id2, player2] = players[1];

            // Remove from queue
            this.queue.delete(id1);
            this.queue.delete(id2);

            // Generate room code
            const roomCode = this.generateRoomCode();

            return {
                roomCode,
                player1: { id: id1, socket: player1.socket, rating: player1.rating },
                player2: { id: id2, socket: player2.socket, rating: player2.rating }
            };
        }

        return null;
    }

    generateRoomCode() {
        const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
        let code = '';
        for (let i = 0; i < 6; i++) {
            code += chars[Math.floor(Math.random() * chars.length)];
        }
        return code;
    }

    // Enhanced ELO-based matching (for future use)
    tryMatchByRating(maxRatingDiff = 200) {
        if (this.queue.size < 2) return null;

        const players = Array.from(this.queue.entries())
            .map(([id, data]) => ({ id, ...data }))
            .sort((a, b) => a.joinTime - b.joinTime);

        // Find compatible match
        for (let i = 0; i < players.length; i++) {
            for (let j = i + 1; j < players.length; j++) {
                const ratingDiff = Math.abs(players[i].rating - players[j].rating);
                const waitTime = Date.now() - Math.min(players[i].joinTime, players[j].joinTime);

                // Increase acceptable rating diff over time
                const adjustedMaxDiff = maxRatingDiff + Math.floor(waitTime / 10000) * 50;

                if (ratingDiff <= adjustedMaxDiff) {
                    // Match found!
                    this.queue.delete(players[i].id);
                    this.queue.delete(players[j].id);

                    return {
                        roomCode: this.generateRoomCode(),
                        player1: players[i],
                        player2: players[j]
                    };
                }
            }
        }

        return null;
    }
}
