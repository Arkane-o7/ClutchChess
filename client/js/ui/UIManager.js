/**
 * Clutch Chess - UI Manager
 * Handles all menu screens, modals, and HUD updates
 */

import { EventEmitter } from '../utils/EventEmitter.js';
import { GAME_CONFIG } from '../../../shared/constants.js';

export class UIManager extends EventEmitter {
    constructor() {
        super();

        // Cache DOM elements
        this.screens = {
            mainMenu: document.getElementById('main-menu'),
            playMenu: document.getElementById('play-menu'),
            matchmaking: document.getElementById('matchmaking-screen'),
            lobby: document.getElementById('lobby-screen'),
            gameOver: document.getElementById('game-over')
        };

        this.modals = {
            join: document.getElementById('join-modal'),
            tutorial: document.getElementById('tutorial-modal'),
            auth: document.getElementById('auth-modal'),
            leaderboard: document.getElementById('leaderboard-modal')
        };

        this.hud = document.getElementById('hud');

        // Mana elements
        this.whiteManaFill = document.getElementById('white-mana-fill');
        this.blackManaFill = document.getElementById('black-mana-fill');

        // Game timer
        this.gameTimer = document.getElementById('game-timer');
        this.gameStartTime = 0;
        this.timerInterval = null;

        // Queue timer
        this.queueStartTime = 0;
        this.queueInterval = null;

        // Auth state
        this.isLoginMode = true;

        this.bindEvents();
    }

    bindEvents() {
        // Main menu
        document.getElementById('btn-play').addEventListener('click', () => {
            this.showPlayMenu();
        });

        document.getElementById('btn-practice').addEventListener('click', () => {
            this.emit('startPractice');
        });

        document.getElementById('btn-how-to-play').addEventListener('click', () => {
            this.showModal('tutorial');
        });

        // Play menu
        document.getElementById('btn-back-play').addEventListener('click', () => {
            this.showMainMenu();
        });

        document.getElementById('btn-find-match').addEventListener('click', () => {
            this.emit('findMatch');
        });

        document.getElementById('btn-create-room').addEventListener('click', () => {
            this.emit('createRoom');
        });

        document.getElementById('btn-join-room').addEventListener('click', () => {
            this.showModal('join');
        });

        // Matchmaking
        document.getElementById('btn-cancel-match').addEventListener('click', () => {
            this.stopQueueTimer();
            this.emit('cancelMatch');
        });

        // Lobby
        document.getElementById('btn-leave-lobby').addEventListener('click', () => {
            this.emit('leaveRoom');
        });

        document.getElementById('btn-copy-code').addEventListener('click', () => {
            this.copyRoomCode();
        });

        // Join modal
        document.getElementById('btn-close-join').addEventListener('click', () => {
            this.hideModal('join');
        });

        document.getElementById('btn-submit-join').addEventListener('click', () => {
            const code = document.getElementById('room-code-input').value.trim().toUpperCase();
            if (code.length >= 4) {
                this.emit('joinRoom', code);
                this.hideModal('join');
            }
        });

        // Tutorial modal
        document.getElementById('btn-close-tutorial').addEventListener('click', () => {
            this.hideModal('tutorial');
        });

        // Game over
        document.getElementById('btn-rematch').addEventListener('click', () => {
            this.emit('rematch');
        });

        document.getElementById('btn-return-menu').addEventListener('click', () => {
            this.emit('returnToMenu');
        });

        // Close modals on backdrop click
        Object.values(this.modals).forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.classList.add('hidden');
                }
            });
        });

        // Room code input formatting
        document.getElementById('room-code-input').addEventListener('input', (e) => {
            e.target.value = e.target.value.toUpperCase();
        });

        // --- Auth Events ---
        document.getElementById('btn-login-open').addEventListener('click', () => {
            this.showModal('auth');
        });

        document.getElementById('btn-auth-submit').addEventListener('click', () => {
            const username = document.getElementById('auth-username').value.trim();
            const password = document.getElementById('auth-password').value.trim();
            if (username && password) {
                this.emit('authSubmit', { username, password, isLogin: this.isLoginMode });
            }
        });

        document.getElementById('btn-auth-switch').addEventListener('click', () => {
            this.toggleAuthMode();
        });

        document.getElementById('btn-logout').addEventListener('click', () => {
            this.emit('logout');
        });

        document.getElementById('btn-close-auth').addEventListener('click', () => {
            this.hideModal('auth');
        });

        // --- Leaderboard Events ---
        document.getElementById('btn-leaderboard').addEventListener('click', () => {
            this.showModal('leaderboard');
            this.emit('fetchLeaderboard');
        });

        document.getElementById('btn-close-leaderboard').addEventListener('click', () => {
            this.hideModal('leaderboard');
        });
    }

    toggleAuthMode() {
        this.isLoginMode = !this.isLoginMode;

        const title = document.getElementById('auth-title');
        const submitBtn = document.getElementById('btn-auth-submit').querySelector('.btn-text');
        const switchText = document.getElementById('auth-switch-text');
        const switchBtn = document.getElementById('btn-auth-switch');

        if (this.isLoginMode) {
            title.textContent = 'LOGIN';
            submitBtn.textContent = 'LOGIN';
            switchText.textContent = 'New here?';
            switchBtn.textContent = 'Create Account';
        } else {
            title.textContent = 'REGISTER';
            submitBtn.textContent = 'CREATE ACCOUNT';
            switchText.textContent = 'Already have an account?';
            switchBtn.textContent = 'Log In';
        }
    }

    // --- UI State Updates ---

    updateAuthState(user) {
        const guestView = document.getElementById('guest-view');
        const userView = document.getElementById('user-view');

        if (user) {
            guestView.classList.add('hidden');
            userView.classList.remove('hidden');
            document.getElementById('user-name-display').textContent = user.username;
            document.getElementById('user-elo-display').textContent = user.elo;
            this.hideModal('auth');
        } else {
            guestView.classList.remove('hidden');
            userView.classList.add('hidden');
        }
    }

    displayLeaderboard(data) {
        const list = document.getElementById('leaderboard-list');
        list.innerHTML = '';

        if (!data || data.length === 0) {
            list.innerHTML = '<div class="leaderboard-loading">No records yet. Be the first!</div>';
            return;
        }

        data.forEach((entry, index) => {
            const el = document.createElement('div');
            el.className = 'leaderboard-item';

            const rankClass = index < 3 ? `top-${index + 1}` : '';

            el.innerHTML = `
                <span class="leaderboard-rank ${rankClass}">#${index + 1}</span>
                <span class="leaderboard-name">${entry.username}</span>
                <span class="leaderboard-elo">${entry.elo}</span>
            `;
            list.appendChild(el);
        });
    }

    showAuthError(message) {
        const errorEl = document.getElementById('auth-error');
        errorEl.textContent = message;
        errorEl.classList.remove('hidden');

        // Remove shake animation class and re-add to trigger it again
        errorEl.style.animation = 'none';
        errorEl.offsetHeight; /* trigger reflow */
        errorEl.style.animation = null;
    }

    // --- Screen Navigation ---

    showScreen(screenName) {
        Object.values(this.screens).forEach(screen => {
            screen.classList.add('hidden');
        });
        if (this.screens[screenName]) {
            this.screens[screenName].classList.remove('hidden');
        }
    }

    showMainMenu() {
        this.showScreen('mainMenu');
        this.hud.classList.add('hidden');
        this.stopGameTimer();
    }

    showPlayMenu() {
        this.showScreen('playMenu');
    }

    showMatchmaking() {
        this.showScreen('matchmaking');
        this.startQueueTimer();
    }

    showLobby(roomCode) {
        this.showScreen('lobby');
        document.getElementById('room-code').textContent = roomCode;
        this.stopQueueTimer();
    }

    showGame() {
        Object.values(this.screens).forEach(screen => {
            screen.classList.add('hidden');
        });
        this.hud.classList.remove('hidden');
        this.startGameTimer();
    }

    showGameOver(result) {
        this.stopGameTimer();

        const title = document.getElementById('game-over-title');
        const subtitle = document.getElementById('game-over-subtitle');

        if (result.victory) {
            title.textContent = 'VICTORY';
            title.className = 'victory';
            subtitle.textContent = 'You have conquered!';
        } else {
            title.textContent = 'DEFEAT';
            title.className = 'defeat';
            subtitle.textContent = 'Your king has fallen...';
        }

        // Stats
        document.getElementById('stat-duration').textContent = this.formatTime(result.duration);
        document.getElementById('stat-captures').textContent = result.captures || 0;

        const eloChange = result.eloChange || 0;
        const eloElement = document.getElementById('stat-elo-change');
        eloElement.textContent = (eloChange >= 0 ? '+' : '') + eloChange;
        eloElement.style.color = eloChange >= 0 ? '#00f0ff' : '#ff0066';

        this.showScreen('gameOver');
        this.hud.classList.add('hidden');
    }

    // --- Modals ---

    showModal(modalName) {
        if (this.modals[modalName]) {
            this.modals[modalName].classList.remove('hidden');
        }
    }

    hideModal(modalName) {
        if (this.modals[modalName]) {
            this.modals[modalName].classList.add('hidden');
        }
    }

    // --- HUD Updates ---

    updateMana(mana) {
        if (this.whiteManaFill) {
            this.whiteManaFill.style.width = (mana.white * 100) + '%';
        }
        if (this.blackManaFill) {
            this.blackManaFill.style.width = (mana.black * 100) + '%';
        }
    }

    setPlayerNames(players) {
        const whiteName = document.getElementById('hud-white-name');
        const blackName = document.getElementById('hud-black-name');

        if (players.white) {
            whiteName.textContent = players.white.username || 'Player 1';
        }
        if (players.black) {
            blackName.textContent = players.black.username || 'Opponent';
        }
    }

    updateLobbyPlayers(players) {
        const whiteSlot = document.getElementById('player-white');
        const blackSlot = document.getElementById('player-black');

        if (players.white) {
            whiteSlot.querySelector('.player-name').textContent = players.white.username || 'Player 1';
            whiteSlot.querySelector('.player-rating').textContent = players.white.rating ? `ELO ${players.white.rating}` : '';
        }

        if (players.black) {
            blackSlot.querySelector('.player-name').textContent = players.black.username || 'Player 2';
            blackSlot.querySelector('.player-rating').textContent = players.black.rating ? `ELO ${players.black.rating}` : '';

            // Enable start button when both players present
            const startBtn = document.getElementById('btn-start-game');
            startBtn.disabled = false;
            startBtn.querySelector('.btn-text').textContent = 'START GAME';
        }
    }

    // --- Timers ---

    startGameTimer() {
        this.gameStartTime = Date.now();
        this.timerInterval = setInterval(() => {
            const elapsed = Math.floor((Date.now() - this.gameStartTime) / 1000);
            this.gameTimer.textContent = this.formatTime(elapsed);
        }, 1000);
    }

    stopGameTimer() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
    }

    startQueueTimer() {
        this.queueStartTime = Date.now();
        const queueTimeEl = document.getElementById('queue-time');

        this.queueInterval = setInterval(() => {
            const elapsed = Math.floor((Date.now() - this.queueStartTime) / 1000);
            queueTimeEl.textContent = this.formatTime(elapsed);
        }, 1000);
    }

    stopQueueTimer() {
        if (this.queueInterval) {
            clearInterval(this.queueInterval);
            this.queueInterval = null;
        }
    }

    formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    // --- Utilities ---

    copyRoomCode() {
        const code = document.getElementById('room-code').textContent;
        navigator.clipboard.writeText(code).then(() => {
            const btn = document.getElementById('btn-copy-code');
            btn.textContent = '✓';
            setTimeout(() => btn.textContent = '📋', 1500);
        });
    }

    showError(message) {
        // Simple error display - could be enhanced with toast notifications
        console.error('[UI Error]', message);
        alert(message);
    }
}
