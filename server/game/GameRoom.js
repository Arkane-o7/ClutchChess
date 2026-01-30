/**
 * Clutch Chess - Game Room
 * Manages a single game instance between two players
 */

import { GAME_CONFIG } from '../../shared/constants.js';

export class GameRoom {
    constructor(roomCode) {
        this.roomCode = roomCode;
        this.players = new Map(); // id -> { socket, color, username, rating }
        this.isPlaying = false;
        this.startTime = null;
        this.gameState = null;
    }

    addPlayer(id, socket, color, userData = null) {
        this.players.set(id, {
            socket,
            color,
            username: userData?.username || `Player ${this.players.size + 1}`,
            rating: userData?.rating || 1000,
            isGuest: userData?.isGuest !== false, // default to true if undefined
            userId: userData?.userId
        });
    }

    removePlayer(id) {
        this.players.delete(id);
    }

    hasPlayer(id) {
        return this.players.has(id);
    }

    isFull() {
        return this.players.size >= 2;
    }

    isEmpty() {
        return this.players.size === 0;
    }

    getPlayerByColor(color) {
        for (const player of this.players.values()) {
            if (player.color === color) return player;
        }
        return null;
    }

    getPlayersInfo() {
        const info = { white: null, black: null };
        this.players.forEach((player, id) => {
            info[player.color] = {
                id,
                username: player.username,
                rating: player.rating
            };
        });
        return info;
    }

    startGame() {
        this.isPlaying = true;
        this.startTime = Date.now();
        this.gameState = this.createInitialState();

        // Assign colors to socket objects for easy lookup
        this.players.forEach((player, id) => {
            player.socket.gameColor = player.color;
        });
    }

    createInitialState() {
        // Create piece layout
        // Standard chess: Black at top (rows 0-1), White at bottom (rows 6-7)
        const pieces = [];
        const layout = [
            ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r'],  // Row 0 - Black back rank
            ['p', 'p', 'p', 'p', 'p', 'p', 'p', 'p'],  // Row 1 - Black pawns
            [null, null, null, null, null, null, null, null],
            [null, null, null, null, null, null, null, null],
            [null, null, null, null, null, null, null, null],
            [null, null, null, null, null, null, null, null],
            ['P', 'P', 'P', 'P', 'P', 'P', 'P', 'P'],  // Row 6 - White pawns
            ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R']   // Row 7 - White back rank
        ];

        for (let row = 0; row < 8; row++) {
            for (let col = 0; col < 8; col++) {
                const char = layout[row][col];
                if (char) {
                    const isWhite = char === char.toUpperCase();
                    pieces.push({
                        id: `${char.toLowerCase()}-${row}-${col}`,
                        type: char.toLowerCase(),
                        isWhite,
                        col,
                        row,
                        x: col * GAME_CONFIG.TILE_SIZE + GAME_CONFIG.TILE_SIZE / 2,
                        y: row * GAME_CONFIG.TILE_SIZE + GAME_CONFIG.TILE_SIZE / 2
                    });
                }
            }
        }

        return {
            pieces,
            whiteMana: GAME_CONFIG.MANA_START,
            blackMana: GAME_CONFIG.MANA_START
        };
    }

    getGameState() {
        return this.gameState;
    }

    validateMove(playerId, move) {
        const player = this.players.get(playerId);
        if (!player) return false;

        // Find the piece
        const piece = this.gameState.pieces.find(p => p.id === move.pieceId);
        if (!piece) return false;

        // Check if player owns this piece
        const playerIsWhite = player.color === 'white';
        if (piece.isWhite !== playerIsWhite) return false;

        // Regenerate mana based on elapsed time
        const elapsed = (Date.now() - this.startTime) / 1000; // seconds
        const regenAmount = elapsed * GAME_CONFIG.MANA_REGEN_PER_SECOND;

        // Calculate expected mana (start + regen - spent)
        // We track spent mana separately to avoid accumulation errors
        if (!this.gameState.whiteManaSpent) this.gameState.whiteManaSpent = 0;
        if (!this.gameState.blackManaSpent) this.gameState.blackManaSpent = 0;

        const whiteManaRaw = GAME_CONFIG.MANA_START + regenAmount - this.gameState.whiteManaSpent;
        const blackManaRaw = GAME_CONFIG.MANA_START + regenAmount - this.gameState.blackManaSpent;

        this.gameState.whiteMana = Math.min(GAME_CONFIG.MANA_MAX, whiteManaRaw);
        this.gameState.blackMana = Math.min(GAME_CONFIG.MANA_MAX, blackManaRaw);

        // Check mana
        const mana = playerIsWhite ? this.gameState.whiteMana : this.gameState.blackMana;
        if (mana < GAME_CONFIG.MANA_COST_PER_MOVE) return false;

        // Deduct mana (track spent amount)
        if (playerIsWhite) {
            this.gameState.whiteManaSpent += GAME_CONFIG.MANA_COST_PER_MOVE;
        } else {
            this.gameState.blackManaSpent += GAME_CONFIG.MANA_COST_PER_MOVE;
        }

        // Basic move validation (could be more sophisticated)
        if (move.to.col < 0 || move.to.col >= 8 || move.to.row < 0 || move.to.row >= 8) {
            return false;
        }

        // Update server-side state
        piece.col = move.to.col;
        piece.row = move.to.row;
        piece.x = move.to.col * GAME_CONFIG.TILE_SIZE + GAME_CONFIG.TILE_SIZE / 2;
        piece.y = move.to.row * GAME_CONFIG.TILE_SIZE + GAME_CONFIG.TILE_SIZE / 2;

        return true;
    }

    endGame(result) {
        this.isPlaying = false;
    }
}
