/**
 * Leaderboard Component
 *
 * Displays top 100 player rankings for a selected rating mode.
 */

import { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { getLeaderboard } from '../api/client';
import type { LeaderboardEntry } from '../api/types';
import { useAuthStore } from '../stores/auth';
import { RATING_MODES, formatModeName, type RatingMode } from '../utils/ratings';
import BeltIcon from './BeltIcon';
import PlayerBadge from './PlayerBadge';
import './Leaderboard.css';

interface LeaderboardProps {
  initialMode?: RatingMode;
}

export function Leaderboard({ initialMode = '2p_standard' }: LeaderboardProps) {
  const user = useAuthStore((s) => s.user);

  const [mode, setMode] = useState<RatingMode>(initialMode);
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchLeaderboard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getLeaderboard(mode);
      setEntries(data.entries);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load leaderboard');
    } finally {
      setLoading(false);
    }
  }, [mode]);

  useEffect(() => {
    fetchLeaderboard();
  }, [fetchLeaderboard]);

  return (
    <div className="leaderboard">
      <div className="leaderboard-header">
        <select
          value={mode}
          onChange={(e) => setMode(e.target.value as RatingMode)}
          className="mode-selector"
        >
          {RATING_MODES.map((m) => (
            <option key={m} value={m}>
              {formatModeName(m)}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="leaderboard-loading">Loading leaderboard...</div>
      ) : error ? (
        <div className="leaderboard-error">
          <p>{error}</p>
          <button className="btn btn-primary" onClick={fetchLeaderboard}>
            Retry
          </button>
        </div>
      ) : entries.length === 0 ? (
        <div className="leaderboard-empty">
          <p>No ranked players yet for {formatModeName(mode)}.</p>
          <p>Be the first to play a ranked game!</p>
          <Link to="/lobbies" className="btn btn-primary">
            Find a Game
          </Link>
        </div>
      ) : (
        <table className="leaderboard-table">
          <thead>
            <tr>
              <th className="col-rank">#</th>
              <th className="col-belt"></th>
              <th className="col-player">Player</th>
              <th className="col-rating">Rating</th>
              <th className="col-record">W-L</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry) => (
              <tr
                key={entry.user_id}
                className={user?.id === entry.user_id ? 'highlight-row' : ''}
              >
                <td className="col-rank">{entry.rank}</td>
                <td className="col-belt">
                  <BeltIcon belt={entry.belt} />
                </td>
                <td className="col-player">
                  <PlayerBadge
                    userId={entry.user_id}
                    username={entry.username}
                    pictureUrl={entry.picture_url}
                    size="sm"
                  />
                </td>
                <td className="col-rating">{entry.rating}</td>
                <td className="col-record">
                  {entry.wins}-{entry.games_played - entry.wins}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
