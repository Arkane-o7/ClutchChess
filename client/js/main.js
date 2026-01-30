/**
 * Clutch Chess - Main Entry Point
 * Initializes the game engine, UI, and network components
 */

import { GameEngine } from './game/GameEngine.js';
import { UIManager } from './ui/UIManager.js';
import { SocketClient } from './network/SocketClient.js';
import { AuthService } from './network/AuthService.js';

class ClutchChess {
    constructor() {
        this.ui = null;
        this.game = null;
        this.network = null;
        this.auth = null;
        this.isMultiplayer = false;
        this.playerColor = 'white';
    }

    async init() {
        console.log('🎮 Clutch Chess initializing...');

        // Initialize UI Manager
        this.ui = new UIManager();
        this.ui.on('startPractice', () => this.startPracticeGame());
        this.ui.on('findMatch', () => this.startMatchmaking());
        this.ui.on('cancelMatch', () => this.cancelMatchmaking());
        this.ui.on('createRoom', () => this.createRoom());
        this.ui.on('joinRoom', (code) => this.joinRoom(code));
        this.ui.on('leaveRoom', () => this.leaveRoom());
        this.ui.on('returnToMenu', () => this.returnToMenu());

        // Auth Events
        this.ui.on('authSubmit', (data) => this.handleAuth(data));
        this.ui.on('logout', () => this.handleLogout());
        this.ui.on('fetchLeaderboard', () => this.updateLeaderboard());

        // Initialize Network
        this.network = new SocketClient();
        this.network.on('matchFound', (data) => this.onMatchFound(data));
        this.network.on('roomCreated', (data) => this.onRoomCreated(data));
        this.network.on('roomJoined', (data) => this.onRoomJoined(data));
        this.network.on('gameStart', (data) => this.onGameStart(data));
        this.network.on('opponentMove', (data) => this.onOpponentMove(data));
        this.network.on('gameOver', (data) => this.onGameOver(data));
        this.network.on('playerLeft', () => this.onOpponentDisconnect());
        this.network.on('error', (error) => this.ui.showError(error));

        // Initialize Game Engine (but don't start yet)
        this.game = new GameEngine(document.getElementById('canvas-container'));
        this.game.on('movePiece', (move) => this.onPlayerMove(move));
        this.game.on('gameOver', (result) => this.onLocalGameOver(result));
        this.game.on('manaUpdate', (mana) => this.ui.updateMana(mana));

        // Initialize AuthService
        this.auth = new AuthService();
        const user = await this.auth.fetchProfile();
        this.ui.updateAuthState(user);

        // Start animation loop
        this.game.startRenderLoop();

        console.log('✅ Clutch Chess ready!');
    }

    // --- Auth Handlers ---

    async handleAuth({ username, password, isLogin }) {
        try {
            let user;
            if (isLogin) {
                user = await this.auth.login(username, password);
            } else {
                user = await this.auth.register(username, password);
            }
            this.ui.updateAuthState(user);
        } catch (error) {
            this.ui.showAuthError(error.message);
        }
    }

    handleLogout() {
        this.auth.logout();
        this.ui.updateAuthState(null);
    }

    async updateLeaderboard() {
        const data = await this.auth.getLeaderboard();
        this.ui.displayLeaderboard(data);
    }

    // --- Game Modes ---

    startPracticeGame() {
        console.log('🤖 Starting practice game vs AI');
        this.isMultiplayer = false;
        this.playerColor = 'white';
        this.game.startGame({ vsAI: true, playerColor: 'white' });
        this.ui.showGame();
    }

    startMatchmaking() {
        console.log('🔍 Starting matchmaking');
        this.network.findMatch(this.auth.getToken());
        this.ui.showMatchmaking();
    }

    cancelMatchmaking() {
        this.network.cancelMatch();
        this.ui.showPlayMenu();
    }

    createRoom() {
        this.network.createRoom(this.auth.getToken());
    }

    joinRoom(code) {
        this.network.joinRoom(code, this.auth.getToken());
    }

    leaveRoom() {
        this.network.leaveRoom();
        this.ui.showPlayMenu();
    }

    returnToMenu() {
        this.game.reset();
        this.ui.showMainMenu();
    }

    // --- Network Callbacks ---

    onMatchFound(data) {
        console.log('⚔️ Match found!', data);
        this.isMultiplayer = true;
        this.playerColor = data.color;
        this.ui.updateLobbyPlayers(data.players);
        this.ui.showLobby(data.roomCode);
    }

    onRoomCreated(data) {
        console.log('🏠 Room created:', data.roomCode);
        this.isMultiplayer = true;
        this.playerColor = data.color; // 'white' for room creator
        this.ui.showLobby(data.roomCode);
    }

    onRoomJoined(data) {
        console.log('🚪 Joined room:', data.roomCode);
        this.isMultiplayer = true;
        this.playerColor = data.color;
        this.ui.updateLobbyPlayers(data.players);
        this.ui.showLobby(data.roomCode);
    }

    onGameStart(data) {
        console.log('🎮 Game starting!', data);
        // data usually doesn't contain color, we already have it from match/room events

        this.game.startGame({
            vsAI: false,
            playerColor: this.playerColor,
            initialState: data.gameState
        });
        this.ui.showGame();
        this.ui.setPlayerNames(data.players);
    }

    onOpponentMove(data) {
        this.game.applyOpponentMove(data);
    }

    onLocalGameOver(result) {
        if (this.isMultiplayer) {
            this.network.reportGameOver(result);
        }
        this.showGameOver(result);
    }

    onGameOver(data) {
        this.showGameOver(data);
    }

    showGameOver(result) {
        const playerWon = result.winner === this.playerColor;
        this.ui.showGameOver({
            victory: playerWon,
            duration: result.duration,
            captures: result.captures,
            eloChange: result.eloChange || 0
        });
    }

    onOpponentDisconnect() {
        // Opponent left - you win by forfeit!
        console.log('👋 Opponent disconnected');
        this.game.isPlaying = false;
        this.ui.showGameOver({
            victory: true,
            duration: Math.floor(this.game.gameTime),
            captures: 'Opponent disconnected',
            eloChange: 0
        });
    }

    // --- Player Actions ---

    onPlayerMove(move) {
        if (this.isMultiplayer) {
            this.network.sendMove(move);
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const app = new ClutchChess();
    app.init().catch(console.error);
});
