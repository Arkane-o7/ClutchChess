/**
 * Replays Page
 *
 * Lists recent game replays that can be watched.
 */

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { listReplays } from '../api/client';
import type { ApiReplaySummary } from '../api/types';
import { formatDate, formatDuration, formatWinReason } from '../utils/format';
import PlayerBadge from '../components/PlayerBadge';
import './Replays.css';

export function Replays() {
  const [replays, setReplays] = useState<ApiReplaySummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchReplays() {
      try {
        setLoading(true);
        const response = await listReplays(10);
        setReplays(response.replays);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load replays');
      } finally {
        setLoading(false);
      }
    }

    fetchReplays();
  }, []);

  if (loading) {
    return (
      <div className="replays-page">
        <div className="replays-loading">Loading replays...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="replays-page">
        <div className="replays-error">
          <h2>Error</h2>
          <p>{error}</p>
          <Link to="/" className="replays-back-link">Back to Home</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="replays-page">
      <h1>Recent Replays</h1>

      {replays.length === 0 ? (
        <div className="replays-empty">
          <p>No replays available yet.</p>
          <p>Play a game to create your first replay!</p>
          <Link to="/" className="replays-back-link">Back to Home</Link>
        </div>
      ) : (
        <div className="replays-list">
          {replays.map((replay) => (
            <Link
              key={replay.game_id}
              to={`/replay/${replay.game_id}`}
              className="replay-card"
            >
              <div className="replay-card-header">
                <span className="replay-card-date">{formatDate(replay.created_at)}</span>
                <span className="replay-card-speed">{replay.speed}</span>
              </div>

              <div className="replay-card-players">
                {Object.entries(replay.players).map(([num, player]) => (
                  <span
                    key={num}
                    className={`replay-card-player ${replay.winner === parseInt(num) ? 'winner' : ''}`}
                  >
                    <PlayerBadge
                      userId={player.user_id}
                      username={player.name || `Player ${num}`}
                      pictureUrl={player.picture_url}
                      size="sm"
                      linkToProfile={false}
                    />
                    {replay.winner === parseInt(num) && ' (W)'}
                  </span>
                ))}
              </div>

              <div className="replay-card-footer">
                <span className="replay-card-duration">{formatDuration(replay.total_ticks)}</span>
                {replay.win_reason && (
                  <span className="replay-card-result">{formatWinReason(replay.win_reason)}</span>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
