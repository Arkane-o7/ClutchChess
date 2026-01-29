/**
 * Clutch Chess - Socket Client
 * Handles real-time communication with the game server
 */

import { io } from 'socket.io-client';
import { EventEmitter } from '../utils/EventEmitter.js';
import { SOCKET_EVENTS } from '../../../shared/constants.js';

export class SocketClient extends EventEmitter {
    constructor() {
        super();
        this.socket = null;
        this.connected = false;
        this.roomCode = null;
        this.playerId = null;
    }

    connect() {
        if (this.socket) return Promise.resolve();

        return new Promise((resolve, reject) => {
            // Connect to game server (same origin in production, or localhost in dev)
            const url = window.location.hostname === 'localhost'
                ? 'http://localhost:3000'
                : window.location.origin;

            this.socket = io(url, {
                transports: ['websocket'],
                autoConnect: true
            });

            this.socket.on('connect', () => {
                console.log('🔌 Connected to server');
                this.connected = true;
                this.playerId = this.socket.id;
                resolve();
            });

            this.socket.on('connect_error', (error) => {
                console.error('🔌 Connection error:', error);
                // Don't reject - allow offline/practice mode
                resolve();
            });

            this.socket.on('disconnect', () => {
                console.log('🔌 Disconnected from server');
                this.connected = false;
            });

            // Set up event listeners
            this.setupEventListeners();
        });
    }

    setupEventListeners() {
        // Matchmaking
        this.socket.on(SOCKET_EVENTS.MATCH_FOUND, (data) => {
            this.roomCode = data.roomCode;
            this.emit('matchFound', data);
        });

        // Room events
        this.socket.on(SOCKET_EVENTS.ROOM_CREATED, (data) => {
            this.roomCode = data.roomCode;
            this.emit('roomCreated', data);
        });

        this.socket.on(SOCKET_EVENTS.ROOM_JOINED, (data) => {
            this.roomCode = data.roomCode;
            this.emit('roomJoined', data);
        });

        this.socket.on(SOCKET_EVENTS.ROOM_ERROR, (data) => {
            this.emit('error', data.message);
        });

        this.socket.on(SOCKET_EVENTS.PLAYER_JOINED, (data) => {
            this.emit('playerJoined', data);
        });

        this.socket.on(SOCKET_EVENTS.PLAYER_LEFT, (data) => {
            this.emit('playerLeft', data);
        });

        // Game events
        this.socket.on(SOCKET_EVENTS.GAME_START, (data) => {
            this.emit('gameStart', data);
        });

        this.socket.on(SOCKET_EVENTS.PIECE_MOVED, (data) => {
            // Only process opponent's moves
            if (data.playerId !== this.playerId) {
                this.emit('opponentMove', data);
            }
        });

        this.socket.on(SOCKET_EVENTS.GAME_STATE, (data) => {
            this.emit('gameState', data);
        });

        this.socket.on(SOCKET_EVENTS.GAME_OVER, (data) => {
            this.emit('gameOver', data);
        });
    }

    // --- Actions ---

    findMatch(token) {
        if (!this.connected) {
            this.connect().then(() => {
                if (this.connected) {
                    this.socket.emit(SOCKET_EVENTS.FIND_MATCH, { token });
                } else {
                    this.emit('error', 'Could not connect to server. Try Practice mode.');
                }
            });
        } else {
            this.socket.emit(SOCKET_EVENTS.FIND_MATCH, { token });
        }
    }

    cancelMatch() {
        if (this.connected) {
            this.socket.emit(SOCKET_EVENTS.CANCEL_MATCH);
        }
    }

    createRoom(token) {
        if (!this.connected) {
            this.connect().then(() => {
                if (this.connected) {
                    this.socket.emit(SOCKET_EVENTS.CREATE_ROOM, { token });
                } else {
                    this.emit('error', 'Could not connect to server.');
                }
            });
        } else {
            this.socket.emit(SOCKET_EVENTS.CREATE_ROOM, { token });
        }
    }

    joinRoom(code, token) {
        if (!this.connected) {
            this.connect().then(() => {
                if (this.connected) {
                    this.socket.emit(SOCKET_EVENTS.JOIN_ROOM, { roomCode: code, token });
                } else {
                    this.emit('error', 'Could not connect to server.');
                }
            });
        } else {
            this.socket.emit(SOCKET_EVENTS.JOIN_ROOM, { roomCode: code, token });
        }
    }

    leaveRoom() {
        if (this.connected && this.roomCode) {
            this.socket.emit('leave_room', { roomCode: this.roomCode });
            this.roomCode = null;
        }
    }

    sendMove(move) {
        if (this.connected && this.roomCode) {
            this.socket.emit(SOCKET_EVENTS.MOVE_PIECE, {
                roomCode: this.roomCode,
                playerId: this.playerId,
                ...move
            });
        }
    }

    reportGameOver(result) {
        if (this.connected && this.roomCode) {
            this.socket.emit(SOCKET_EVENTS.GAME_OVER, {
                roomCode: this.roomCode,
                ...result
            });
        }
    }
}
