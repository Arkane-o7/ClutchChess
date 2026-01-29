/**
 * Clutch Chess - Game Server
 * Express + Socket.IO server for real-time multiplayer
 */

import express from 'express';
import { createServer } from 'http';
import { Server } from 'socket.io';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { GameRoom } from './game/GameRoom.js';
import { MatchMaker } from './game/MatchMaker.js';
import { SOCKET_EVENTS } from '../shared/constants.js';

import { AuthController } from './controllers/AuthController.js';
import { authMiddleware } from './middleware/auth.js';
import { GAME_CONFIG } from '../shared/constants.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const app = express();
const server = createServer(app);
const io = new Server(server, {
    cors: {
        origin: ['http://localhost:5173', 'http://localhost:3000'],
        methods: ['GET', 'POST']
    }
});

// Middleware
app.use(express.json()); // Enable JSON body parsing for API

// Game state
const rooms = new Map();
const matchMaker = new MatchMaker();

// Initialize Database
AuthController.init().catch(console.error);

// Serve static files in production
app.use(express.static(join(__dirname, '../dist')));

// API routes
app.get('/api/health', (req, res) => {
    res.json({ status: 'ok', rooms: rooms.size, queue: matchMaker.getQueueSize() });
});

// Auth Routes
app.post('/api/auth/register', AuthController.register);
app.post('/api/auth/login', AuthController.login);
app.get('/api/auth/me', authMiddleware, AuthController.getMe);
app.get('/api/leaderboard', AuthController.getLeaderboard);

// Socket.IO connection handling
io.on('connection', (socket) => {
    console.log(`🔌 Player connected: ${socket.id}`);

    // --- Matchmaking ---

    socket.on(SOCKET_EVENTS.FIND_MATCH, async (data) => {
        let playerData = {
            id: socket.id,
            username: `Guest ${socket.id.substring(0, 4)}`,
            rating: 1000,
            isGuest: true
        };

        // verify token if provided
        if (data?.token) {
            const user = AuthController.verifyToken(data.token);
            if (user) {
                // Get fresh data from DB
                const dbUser = await AuthController.getUser(user.username);
                if (dbUser) {
                    playerData = {
                        id: socket.id, // Socket ID is still used for routing
                        userId: dbUser.id, // Database ID
                        username: dbUser.username,
                        rating: dbUser.elo,
                        isGuest: false
                    };
                }
            }
        }

        console.log(`🔍 Player ${playerData.username} (${playerData.rating}) looking for match`);
        matchMaker.addToQueue(socket.id, socket, playerData);

        // Try to create a match
        // Try to create a match
        const match = matchMaker.tryMatchByRating(); // Use ELO matchmaking
        if (match) {
            const room = new GameRoom(match.roomCode);
            room.addPlayer(match.player1.id, match.player1.socket, 'white', match.player1.data);
            room.addPlayer(match.player2.id, match.player2.socket, 'black', match.player2.data);
            rooms.set(match.roomCode, room);

            // Notify both players
            match.player1.socket.join(match.roomCode);
            match.player2.socket.join(match.roomCode);

            match.player1.socket.emit(SOCKET_EVENTS.MATCH_FOUND, {
                roomCode: match.roomCode,
                color: 'white',
                players: room.getPlayersInfo()
            });

            match.player2.socket.emit(SOCKET_EVENTS.MATCH_FOUND, {
                roomCode: match.roomCode,
                color: 'black',
                players: room.getPlayersInfo()
            });

            // Auto-start game after short delay
            setTimeout(() => {
                room.startGame();
                io.to(match.roomCode).emit(SOCKET_EVENTS.GAME_START, {
                    gameState: room.getGameState(),
                    players: room.getPlayersInfo()
                });
            }, 2000);
        }
    });

    socket.on(SOCKET_EVENTS.CANCEL_MATCH, () => {
        matchMaker.removeFromQueue(socket.id);
        console.log(`❌ Player ${socket.id} cancelled matchmaking`);
    });

    // --- Private Rooms ---

    socket.on(SOCKET_EVENTS.CREATE_ROOM, async (data) => {
        const roomCode = generateRoomCode();
        const room = new GameRoom(roomCode);

        // Resolve user
        let userData = null;
        if (data?.token) {
            const user = AuthController.verifyToken(data.token);
            if (user) {
                const dbUser = await AuthController.getUser(user.username);
                if (dbUser) userData = { username: dbUser.username, rating: dbUser.elo, isGuest: false, userId: dbUser.id };
            }
        }

        room.addPlayer(socket.id, socket, 'white', userData);
        rooms.set(roomCode, room);

        socket.join(roomCode);
        socket.emit(SOCKET_EVENTS.ROOM_CREATED, {
            roomCode,
            color: 'white',
            players: room.getPlayersInfo()
        });

        console.log(`🏠 Room created: ${roomCode} by ${socket.id}`);
    });

    socket.on(SOCKET_EVENTS.JOIN_ROOM, async (data) => {
        const { roomCode, token } = data;
        const room = rooms.get(roomCode?.toUpperCase());

        if (!room) {
            socket.emit(SOCKET_EVENTS.ROOM_ERROR, { message: 'Room not found' });
            return;
        }

        if (room.isFull()) {
            socket.emit(SOCKET_EVENTS.ROOM_ERROR, { message: 'Room is full' });
            return;
        }

        // Resolve user
        let userData = null;
        if (token) {
            const user = AuthController.verifyToken(token);
            if (user) {
                const dbUser = await AuthController.getUser(user.username);
                if (dbUser) userData = { username: dbUser.username, rating: dbUser.elo, isGuest: false, userId: dbUser.id };
            }
        }

        room.addPlayer(socket.id, socket, 'black', userData);
        socket.join(roomCode);

        socket.emit(SOCKET_EVENTS.ROOM_JOINED, {
            roomCode,
            color: 'black',
            players: room.getPlayersInfo()
        });

        // Notify the other player
        socket.to(roomCode).emit(SOCKET_EVENTS.PLAYER_JOINED, {
            players: room.getPlayersInfo()
        });

        console.log(`🚪 Player ${socket.id} joined room: ${roomCode}`);

        // Auto-start game when room is full
        if (room.isFull()) {
            setTimeout(() => {
                room.startGame();
                io.to(roomCode).emit(SOCKET_EVENTS.GAME_START, {
                    gameState: room.getGameState(),
                    players: room.getPlayersInfo()
                });
            }, 1500);
        }
    });

    // --- Game Actions ---

    socket.on(SOCKET_EVENTS.MOVE_PIECE, (data) => {
        const room = rooms.get(data.roomCode);
        if (!room || !room.isPlaying) return;

        // Validate and broadcast move
        if (room.validateMove(socket.id, data)) {
            // Broadcast to all players in room (including sender for confirmation)
            io.to(data.roomCode).emit(SOCKET_EVENTS.PIECE_MOVED, {
                playerId: socket.id,
                pieceId: data.pieceId,
                from: data.from,
                to: data.to
            });
        }
    });

    socket.on(SOCKET_EVENTS.GAME_OVER, async (data) => {
        const room = rooms.get(data.roomCode);
        if (!room) return;

        room.endGame(data);

        // Calculate and Update ELO if both are authenticated
        const p1 = room.getPlayerByColor('white');
        const p2 = room.getPlayerByColor('black');
        let eloChange = 0;

        if (p1 && p2 && !p1.isGuest && !p2.isGuest) {
            const K = 32;
            const expectedScore1 = 1 / (1 + Math.pow(10, (p2.rating - p1.rating) / 400));
            const actualScore1 = data.winner === 'white' ? 1 : 0;

            eloChange = Math.round(K * (actualScore1 - expectedScore1));

            // Update in DB
            await AuthController.updateUserElo(p1.username, eloChange, data.winner === 'white');
            await AuthController.updateUserElo(p2.username, -eloChange, data.winner === 'black');
        }

        io.to(data.roomCode).emit(SOCKET_EVENTS.GAME_OVER, {
            winner: data.winner,
            duration: data.duration,
            captures: data.captures,
            eloChange: Math.abs(eloChange)
        });

        console.log(`🏁 Game over in room ${data.roomCode}, winner: ${data.winner}, elo: ${eloChange}`);
    });

    // --- Disconnection ---

    socket.on('disconnect', () => {
        console.log(`🔌 Player disconnected: ${socket.id}`);

        // Remove from matchmaking queue
        matchMaker.removeFromQueue(socket.id);

        // Handle room cleanup
        rooms.forEach((room, roomCode) => {
            if (room.hasPlayer(socket.id)) {
                room.removePlayer(socket.id);

                // Notify remaining player
                socket.to(roomCode).emit(SOCKET_EVENTS.PLAYER_LEFT, {
                    playerId: socket.id
                });

                // Clean up empty rooms
                if (room.isEmpty()) {
                    rooms.delete(roomCode);
                    console.log(`🗑️ Room ${roomCode} deleted (empty)`);
                }
            }
        });
    });
});

// Room code generator
function generateRoomCode() {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    let code = '';
    for (let i = 0; i < 6; i++) {
        code += chars[Math.floor(Math.random() * chars.length)];
    }
    // Ensure uniqueness
    if (rooms.has(code)) return generateRoomCode();
    return code;
}

// Start server
const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
    console.log(`🚀 Clutch Chess server running on port ${PORT}`);
});
