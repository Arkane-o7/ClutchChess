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
        const pieces = [];
        const layout = [
            ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R'],
            ['P', 'P', 'P', 'P', 'P', 'P', 'P', 'P'],
            [null, null, null, null, null, null, null, null],
            [null, null, null, null, null, null, null, null],
            [null, null, null, null, null, null, null, null],
            [null, null, null, null, null, null, null, null],
            ['p', 'p', 'p', 'p', 'p', 'p', 'p', 'p'],
            ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r']
        ];

        for (let row = 0; row < 8; row++) {
            for (let col = 0; col < 8; col++) {
                const char = layout[row][col];
                if (char) {
                    const isWhite = char === char.toLowerCase();
                    pieces.push({
                        id: `${char}-${row}-${col}`,
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

        // Check mana
        const mana = playerIsWhite ? this.gameState.whiteMana : this.gameState.blackMana;
        if (mana < GAME_CONFIG.MANA_COST_PER_MOVE) return false;

        // Deduct mana
        if (playerIsWhite) {
            this.gameState.whiteMana -= GAME_CONFIG.MANA_COST_PER_MOVE;
        } else {
            this.gameState.blackMana -= GAME_CONFIG.MANA_COST_PER_MOVE;
        }

        // Basic move validation (could be more sophisticated)
        if (move.to.col < 0 || move.to.col >= 8 || move.to.row < 0 || move.to.row >= 8) {
            return false;
        }

        return true;
    }

    endGame(result) {
        this.isPlaying = false;
    }
}
