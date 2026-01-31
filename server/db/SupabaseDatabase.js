/**
 * Clutch Chess - Supabase Database
 * Persistent cloud database for user accounts and leaderboards
 */

import { createClient } from '@supabase/supabase-js';

export class SupabaseDatabase {
    constructor() {
        const supabaseUrl = process.env.SUPABASE_URL;
        const supabaseKey = process.env.SUPABASE_ANON_KEY;

        if (!supabaseUrl || !supabaseKey) {
            console.warn('⚠️ Supabase credentials not found, falling back to in-memory storage');
            this.client = null;
            this.users = new Map(); // Fallback for local dev
        } else {
            this.client = createClient(supabaseUrl, supabaseKey);
            console.log('✅ Connected to Supabase');
        }

        this.initialized = true;
    }

    async init() {
        // Supabase client is ready immediately, no async init needed
        this.initialized = true;
    }

    async createUser(username, passwordHash) {
        if (!this.client) {
            // Fallback for local development
            if (this.users.has(username)) throw new Error('User already exists');
            const user = {
                id: crypto.randomUUID(),
                username,
                password: passwordHash,
                elo: 1000,
                wins: 0,
                losses: 0,
                matches: 0,
                created_at: new Date().toISOString()
            };
            this.users.set(username, user);
            return this.sanitize(user);
        }

        // Check if user exists
        const { data: existing } = await this.client
            .from('users')
            .select('username')
            .eq('username', username)
            .single();

        if (existing) {
            throw new Error('User already exists');
        }

        // Create new user
        const { data, error } = await this.client
            .from('users')
            .insert({
                username,
                password: passwordHash,
                elo: 1000,
                wins: 0,
                losses: 0,
                matches: 0
            })
            .select()
            .single();

        if (error) {
            console.error('Supabase create user error:', error);
            throw new Error('Failed to create user');
        }

        return this.sanitize(data);
    }

    async getUser(username) {
        if (!this.client) {
            return this.users.get(username);
        }

        const { data, error } = await this.client
            .from('users')
            .select('*')
            .eq('username', username)
            .single();

        if (error && error.code !== 'PGRST116') { // PGRST116 = not found
            console.error('Supabase get user error:', error);
        }

        return data || null;
    }

    async updateUser(username, updates) {
        if (!this.client) {
            const user = this.users.get(username);
            if (!user) throw new Error('User not found');
            Object.assign(user, updates);
            this.users.set(username, user);
            return this.sanitize(user);
        }

        const { data, error } = await this.client
            .from('users')
            .update(updates)
            .eq('username', username)
            .select()
            .single();

        if (error) {
            console.error('Supabase update user error:', error);
            throw new Error('Failed to update user');
        }

        return this.sanitize(data);
    }

    async getLeaderboard(limit = 10) {
        if (!this.client) {
            return Array.from(this.users.values())
                .sort((a, b) => b.elo - a.elo)
                .slice(0, limit)
                .map(this.sanitize);
        }

        const { data, error } = await this.client
            .from('users')
            .select('id, username, elo, wins, losses, matches')
            .order('elo', { ascending: false })
            .limit(limit);

        if (error) {
            console.error('Supabase leaderboard error:', error);
            return [];
        }

        return data || [];
    }

    sanitize(user) {
        if (!user) return null;
        const { password, ...safeUser } = user;
        return safeUser;
    }
}
