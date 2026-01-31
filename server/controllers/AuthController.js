
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import { SupabaseDatabase } from '../db/SupabaseDatabase.js';

const db = new SupabaseDatabase();
// In production, use environment variable
const JWT_SECRET = process.env.JWT_SECRET || 'clutch-chess-secret-key-change-this';

export class AuthController {
    static async init() {
        await db.init();
    }

    static async register(req, res) {
        try {
            const { username, password } = req.body;

            if (!username || !password) {
                return res.status(400).json({ error: 'Username and password required' });
            }

            if (username.length < 3) {
                return res.status(400).json({ error: 'Username must be at least 3 characters' });
            }

            const existingUser = await db.getUser(username);
            if (existingUser) {
                return res.status(400).json({ error: 'Username already taken' });
            }

            const hashedPassword = await bcrypt.hash(password, 10);
            const user = await db.createUser(username, hashedPassword);

            const token = jwt.sign({ id: user.id, username: user.username }, JWT_SECRET, { expiresIn: '7d' });

            res.json({ user, token });
        } catch (error) {
            console.error('Register error:', error);
            res.status(500).json({ error: 'Internal server error' });
        }
    }

    static async login(req, res) {
        try {
            const { username, password } = req.body;

            const user = await db.getUser(username);

            if (!user || !(await bcrypt.compare(password, user.password))) {
                return res.status(401).json({ error: 'Invalid credentials' });
            }

            const token = jwt.sign({ id: user.id, username: user.username }, JWT_SECRET, { expiresIn: '7d' });

            res.json({ user: db.sanitize(user), token });
        } catch (error) {
            console.error('Login error:', error);
            res.status(500).json({ error: 'Internal server error' });
        }
    }

    static async getMe(req, res) {
        try {
            // req.user is set by auth middleware
            const user = await db.getUser(req.user.username);
            if (!user) return res.status(404).json({ error: 'User not found' });
            res.json({ user: db.sanitize(user) });
        } catch (error) {
            res.status(500).json({ error: 'Internal server error' });
        }
    }

    static async getLeaderboard(req, res) {
        try {
            const leaderboard = await db.getLeaderboard(20);
            res.json(leaderboard);
        } catch (error) {
            res.status(500).json({ error: 'Failed to fetch leaderboard' });
        }
    }

    static verifyToken(token) {
        try {
            return jwt.verify(token, JWT_SECRET);
        } catch (e) {
            return null;
        }
    }

    static async updateUserElo(username, eloChange, isWin) {
        const user = await db.getUser(username);
        if (!user) return;

        const newElo = Math.max(0, user.elo + eloChange);
        await db.updateUser(username, {
            elo: newElo,
            matches: (user.matches || 0) + 1,
            wins: isWin ? (user.wins || 0) + 1 : (user.wins || 0),
            losses: isWin ? (user.losses || 0) : (user.losses || 0) + 1
        });
        return newElo;
    }
}
