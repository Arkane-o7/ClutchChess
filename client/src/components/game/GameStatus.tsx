/**
 * GameStatus Component
 *
 * Displays current game status and connection state.
 */

import { useGameStore } from '../../stores/game';

export function GameStatus() {
  const status = useGameStore((s) => s.status);
  const connectionState = useGameStore((s) => s.connectionState);
  const playerNumber = useGameStore((s) => s.playerNumber);
  const lastError = useGameStore((s) => s.lastError);

  const getStatusText = () => {
    switch (status) {
      case 'waiting':
        return 'Waiting to start...';
      case 'playing':
        return 'Game in progress';
      case 'finished':
        return 'Game over';
      default:
        return 'Unknown';
    }
  };

  const getConnectionText = () => {
    switch (connectionState) {
      case 'disconnected':
        return 'Disconnected';
      case 'connecting':
        return 'Connecting...';
      case 'connected':
        return 'Connected';
      case 'reconnecting':
        return 'Reconnecting...';
      default:
        return 'Unknown';
    }
  };

  const getConnectionColor = () => {
    switch (connectionState) {
      case 'connected':
        return '#4ade80'; // green
      case 'connecting':
      case 'reconnecting':
        return '#fbbf24'; // yellow
      case 'disconnected':
        return '#f87171'; // red
      default:
        return '#9ca3af'; // gray
    }
  };

  const getPlayerLabel = () => {
    if (playerNumber === 0) return 'Spectator';
    const colors = ['', 'White', 'Black', 'Red', 'Blue'];
    return `Player ${playerNumber} (${colors[playerNumber] || 'Unknown'})`;
  };

  return (
    <div className="game-status">
      <div className="game-status-row">
        <span className="game-status-label">Status:</span>
        <span className="game-status-value">{getStatusText()}</span>
      </div>

      <div className="game-status-row">
        <span className="game-status-label">Connection:</span>
        <span className="game-status-value" style={{ color: getConnectionColor() }}>
          {getConnectionText()}
        </span>
      </div>

      <div className="game-status-row">
        <span className="game-status-label">You are:</span>
        <span className="game-status-value">{getPlayerLabel()}</span>
      </div>


      {lastError && (
        <div className="game-status-error">
          {lastError}
        </div>
      )}
    </div>
  );
}
