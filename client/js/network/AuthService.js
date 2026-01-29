
/**
 * AuthService
 * Handles user authentication and profile management
 */
export class AuthService {
    constructor() {
        this.token = localStorage.getItem('clutch_chess_token');
        this.user = null;
    }

    getToken() {
        return this.token;
    }

    isAuthenticated() {
        return !!this.token;
    }

    async login(username, password) {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Login failed');
        }

        const data = await response.json();
        this.setSession(data);
        return data.user;
    }

    async register(username, password) {
        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Registration failed');
        }

        const data = await response.json();
        this.setSession(data);
        return data.user;
    }

    logout() {
        this.token = null;
        this.user = null;
        localStorage.removeItem('clutch_chess_token');
        localStorage.removeItem('clutch_chess_user');
    }

    setSession(data) {
        this.token = data.token;
        this.user = data.user;
        localStorage.setItem('clutch_chess_token', this.token);
        localStorage.setItem('clutch_chess_user', JSON.stringify(this.user));
    }

    async fetchProfile() {
        if (!this.token) return null;

        try {
            const response = await fetch('/api/auth/me', {
                headers: { 'Authorization': `Bearer ${this.token}` }
            });

            if (response.ok) {
                const data = await response.json();
                this.user = data.user;
                localStorage.setItem('clutch_chess_user', JSON.stringify(this.user));
                return this.user;
            } else {
                // Token invalid
                this.logout();
                return null;
            }
        } catch (e) {
            console.error('Failed to fetch profile', e);
            return null;
        }
    }

    async getLeaderboard() {
        try {
            const response = await fetch('/api/leaderboard');
            if (response.ok) return await response.json();
            return [];
        } catch (e) {
            return [];
        }
    }
}
