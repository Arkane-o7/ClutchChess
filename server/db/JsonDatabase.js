
import fs from 'fs/promises';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const DB_PATH = join(__dirname, 'users.json');

export class JsonDatabase {
    constructor() {
        this.users = new Map();
        this.initialized = false;
    }

    async init() {
        try {
            const data = await fs.readFile(DB_PATH, 'utf-8');
            const users = JSON.parse(data);
            this.users = new Map(Object.entries(users));
        } catch (error) {
            if (error.code === 'ENOENT') {
                await this.save();
            } else {
                console.error('Database load error:', error);
            }
        }
        this.initialized = true;
    }

    async save() {
        const obj = Object.fromEntries(this.users);
        await fs.writeFile(DB_PATH, JSON.stringify(obj, null, 2));
    }

    async createUser(username, passwordHash) {
        if (!this.initialized) await this.init();
        if (this.users.has(username)) throw new Error('User already exists');

        const user = {
            id: crypto.randomUUID(),
            username,
            password: passwordHash,
            elo: 1000,
            wins: 0,
            losses: 0,
            matches: 0,
            createdAt: Date.now()
        };

        this.users.set(username, user);
        await this.save();
        return this.sanitize(user);
    }

    async getUser(username) {
        if (!this.initialized) await this.init();
        return this.users.get(username);
    }

    async updateUser(username, updates) {
        if (!this.initialized) await this.init();
        const user = this.users.get(username);
        if (!user) throw new Error('User not found');

        Object.assign(user, updates);
        this.users.set(username, user);
        await this.save();
        return this.sanitize(user);
    }

    async getLeaderboard(limit = 10) {
        if (!this.initialized) await this.init();
        return Array.from(this.users.values())
            .sort((a, b) => b.elo - a.elo)
            .slice(0, limit)
            .map(this.sanitize);
    }

    sanitize(user) {
        const { password, ...safeUser } = user;
        return safeUser;
    }
}
