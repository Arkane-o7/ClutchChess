/**
 * GameOverModal Component
 *
 * Displays when the game ends, showing winner and options.
 */

import { useGameStore } from '../../stores/game';
import { useLobbyStore } from '../../stores/lobby';
import { useNavigate } from 'react-router-dom';

export function GameOverModal() {
  const navigate = useNavigate();
  const status = useGameStore((s) => s.status);
  const winner = useGameStore((s) => s.winner);
  const winReason = useGameStore((s) => s.winReason);
  const playerNumber = useGameStore((s) => s.playerNumber);
  const reset = useGameStore((s) => s.reset);
  const gameId = useGameStore((s) => s.gameId);

  // Lobby state for returning to lobby
  const lobbyCode = useLobbyStore((s) => s.code);
  const returnToLobby = useLobbyStore((s) => s.returnToLobby);
  const clearPendingGame = useLobbyStore((s) => s.clearPendingGame);

  // Only show when game is finished
  if (status !== 'finished') {
    return null;
  }

  const getResultText = () => {
    if (winner === null) {
      return 'Game Over';
    }

    if (winner === 0) {
      return 'Draw!';
    }

    if (winner === playerNumber) {
      return 'You Win!';
    }

    if (playerNumber === 0) {
      const colors = ['', 'White', 'Black', 'Red', 'Blue'];
      return `${colors[winner] || 'Player ' + winner} Wins!`;
    }

    return 'You Lose';
  };

  const getReasonText = () => {
    switch (winReason) {
      case 'king_captured':
        return 'King was captured';
      case 'draw_timeout':
        return 'Game timed out';
      case 'resignation':
        return 'Opponent resigned';
      default:
        return '';
    }
  };

  const getResultClass = () => {
    if (winner === 0) return 'draw';
    if (winner === playerNumber) return 'win';
    if (playerNumber === 0) return 'neutral';
    return 'lose';
  };

  const handleReturnToLobby = () => {
    // Send return_to_lobby message and navigate
    returnToLobby();
    clearPendingGame();
    reset();
    if (lobbyCode) {
      navigate(`/lobby/${lobbyCode}`);
    } else {
      // Try to get lobby code from session storage
      const storedLobbyCode = gameId ? sessionStorage.getItem(`lobbyCode_${gameId}`) : null;
      if (storedLobbyCode) {
        navigate(`/lobby/${storedLobbyCode}`);
      } else {
        navigate('/');
      }
    }
  };

  const handleViewReplay = () => {
    if (gameId) {
      reset();
      navigate(`/replay/${gameId}`);
    }
  };

  const handleBackToHome = () => {
    clearPendingGame();
    reset();
    navigate('/');
  };

  // Check if we came from a lobby
  const hasLobby = lobbyCode || (gameId && sessionStorage.getItem(`lobbyCode_${gameId}`));

  return (
    <div className="game-over-overlay">
      <div className={`game-over-modal ${getResultClass()}`}>
        <h2 className="game-over-title">{getResultText()}</h2>
        {winReason && <p className="game-over-reason">{getReasonText()}</p>}
        <div className="game-over-actions">
          {hasLobby && (
            <button className="game-over-button primary" onClick={handleReturnToLobby}>
              Return to Lobby
            </button>
          )}
          {gameId && (
            <button className="game-over-button secondary" onClick={handleViewReplay}>
              View Replay
            </button>
          )}
          <button className="game-over-button secondary" onClick={handleBackToHome}>
            Back to Home
          </button>
        </div>
      </div>
    </div>
  );
}
