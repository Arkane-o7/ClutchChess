import { Link } from 'react-router-dom';
import './ReplayCard.css';
import PlayerBadge from './PlayerBadge';
import { formatDate, formatDuration, formatWinReason } from '../utils/format';
import type { ApiReplaySummary } from '../api/types';

interface ReplayCardProps {
  replay: ApiReplaySummary;
}

export default function ReplayCard({ replay }: ReplayCardProps) {
  return (
    <Link to={`/replay/${replay.game_id}`} className="match-history-item">
      <div className="match-info">
        <span className="match-date">{formatDate(replay.created_at)}</span>
        <span className="match-speed">{replay.speed}</span>
      </div>
      <div className="match-players">
        {Object.entries(replay.players).map(([num, player]) => (
          <span
            key={num}
            className={`match-player ${replay.winner === parseInt(num) ? 'winner' : ''}`}
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
      <div className="match-result">
        <span className="match-duration">{formatDuration(replay.total_ticks)}</span>
        {replay.win_reason && (
          <span className="match-reason">{formatWinReason(replay.win_reason)}</span>
        )}
      </div>
    </Link>
  );
}
