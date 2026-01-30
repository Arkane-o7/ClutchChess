/**
 * Watch Page
 *
 * Unified page with tabs for Live Games, Replays, and Leaderboard.
 */

import { useState, useEffect, useCallback } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useLobbyStore } from '../stores/lobby';
import { listReplays } from '../api/client';
import type { LobbyListItem, ApiReplaySummary } from '../api/types';
import { Leaderboard } from '../components/Leaderboard';
import PlayerBadge from '../components/PlayerBadge';
import ReplayCard from '../components/ReplayCard';
import './Watch.css';

type TabId = 'live' | 'replays' | 'leaderboard';

// ============================================
// Live Games Tab Content
// ============================================

function LiveGamesTab() {
  const publicLobbies = useLobbyStore((s) => s.publicLobbies);
  const isLoadingLobbies = useLobbyStore((s) => s.isLoadingLobbies);
  const fetchPublicLobbies = useLobbyStore((s) => s.fetchPublicLobbies);

  useEffect(() => {
    fetchPublicLobbies();
  }, [fetchPublicLobbies]);

  // Refresh lobbies periodically
  useEffect(() => {
    const interval = setInterval(() => {
      fetchPublicLobbies();
    }, 10000);
    return () => clearInterval(interval);
  }, [fetchPublicLobbies]);

  // Filter to show only lobbies that are in-game (active games to watch)
  const activeGames = publicLobbies.filter((lobby) => lobby.status === 'in_game');
  const waitingLobbies = publicLobbies.filter((lobby) => lobby.status === 'waiting');

  if (isLoadingLobbies && publicLobbies.length === 0) {
    return <div className="tab-loading">Loading live games...</div>;
  }

  return (
    <div className="live-games-content">
      {activeGames.length > 0 && (
        <section className="games-section">
          <h3>Active Games</h3>
          <div className="games-list">
            {activeGames.map((lobby) => (
              <LiveGameCard key={lobby.id} lobby={lobby} isActive />
            ))}
          </div>
        </section>
      )}

      {waitingLobbies.length > 0 && (
        <section className="games-section">
          <h3>Waiting for Players</h3>
          <div className="games-list">
            {waitingLobbies.map((lobby) => (
              <LiveGameCard key={lobby.id} lobby={lobby} />
            ))}
          </div>
        </section>
      )}

      {publicLobbies.length === 0 && (
        <div className="tab-empty">
          <p>No live games right now.</p>
          <p>Create a lobby to start playing!</p>
          <Link to="/lobbies" className="btn btn-primary">
            Browse Lobbies
          </Link>
        </div>
      )}
    </div>
  );
}

interface LiveGameCardProps {
  lobby: LobbyListItem;
  isActive?: boolean;
}

function LiveGameCard({ lobby, isActive }: LiveGameCardProps) {
  return (
    <Link
      to={isActive && lobby.status === 'in_game' ? `/game/${lobby.code}` : `/lobby/${lobby.code}`}
      className={`game-card ${isActive ? 'active' : ''}`}
    >
      <div className="game-card-info">
        <div className="game-card-host">
          <PlayerBadge
            userId={null}
            username={lobby.hostUsername}
            pictureUrl={lobby.hostPictureUrl}
            size="sm"
            linkToProfile={false}
          />
          's Game
        </div>
        <div className="game-card-details">
          <span className="detail-badge">{lobby.settings.speed}</span>
          <span>{lobby.settings.playerCount}P</span>
          {lobby.settings.isRanked && <span className="ranked-badge">Ranked</span>}
        </div>
      </div>
      <div className="game-card-status">
        {isActive ? (
          <span className="status-live">Live</span>
        ) : (
          <span className="status-waiting">
            {lobby.currentPlayers}/{lobby.playerCount}
          </span>
        )}
      </div>
    </Link>
  );
}

// ============================================
// Replays Tab Content
// ============================================

function ReplaysTab() {
  const [replays, setReplays] = useState<ApiReplaySummary[]>([]);
  const [replaysTotal, setReplaysTotal] = useState(0);
  const [replaysPage, setReplaysPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const pageSize = 10;
  const maxPages = 10; // Cap at 100 replays total
  const totalPages = Math.min(Math.ceil(replaysTotal / pageSize), maxPages);

  const fetchReplays = useCallback(async () => {
    try {
      setLoading(true);
      const response = await listReplays(pageSize, replaysPage * pageSize);
      setReplays(response.replays);
      setReplaysTotal(response.total);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load replays');
    } finally {
      setLoading(false);
    }
  }, [replaysPage]);

  useEffect(() => {
    fetchReplays();
  }, [fetchReplays]);

  if (loading && replays.length === 0) {
    return <div className="tab-loading">Loading replays...</div>;
  }

  if (error) {
    return (
      <div className="tab-error">
        <p>{error}</p>
        <button className="btn btn-primary" onClick={fetchReplays}>
          Retry
        </button>
      </div>
    );
  }

  if (replays.length === 0) {
    return (
      <div className="tab-empty">
        <p>No replays available yet.</p>
        <p>Play a game to create your first replay!</p>
        <Link to="/" className="btn btn-primary">
          Play Now
        </Link>
      </div>
    );
  }

  return (
    <div className="profile-match-history">
      <div className="match-history-list">
        {replays.map((replay) => (
          <ReplayCard key={replay.game_id} replay={replay} />
        ))}
      </div>

      {totalPages > 1 && (
        <div className="match-history-pagination">
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => setReplaysPage((p) => Math.max(0, p - 1))}
            disabled={replaysPage === 0 || loading}
          >
            Previous
          </button>
          <span className="page-info">
            Page {replaysPage + 1} of {totalPages}
          </span>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => setReplaysPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={replaysPage >= totalPages - 1 || loading}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}

// ============================================
// Main Watch Page
// ============================================

export function Watch() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialTab = (searchParams.get('tab') as TabId) || 'live';
  const [activeTab, setActiveTab] = useState<TabId>(initialTab);

  const handleTabChange = (tab: TabId) => {
    setActiveTab(tab);
    setSearchParams({ tab });
  };

  return (
    <div className="watch-page">
      <div className="watch-tabs">
        <button
          className={`tab-button ${activeTab === 'live' ? 'active' : ''}`}
          onClick={() => handleTabChange('live')}
        >
          Live Games
        </button>
        <button
          className={`tab-button ${activeTab === 'replays' ? 'active' : ''}`}
          onClick={() => handleTabChange('replays')}
        >
          Replays
        </button>
        <button
          className={`tab-button ${activeTab === 'leaderboard' ? 'active' : ''}`}
          onClick={() => handleTabChange('leaderboard')}
        >
          Leaderboard
        </button>
      </div>

      <div className="watch-content">
        {activeTab === 'live' && <LiveGamesTab />}
        {activeTab === 'replays' && <ReplaysTab />}
        {activeTab === 'leaderboard' && <Leaderboard />}
      </div>
    </div>
  );
}
