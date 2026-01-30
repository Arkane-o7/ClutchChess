/**
 * ResignButton Component
 *
 * Resign button with confirmation modal.
 */

import { useState } from 'react';
import { useGameStore, selectIsPlayerEliminated } from '../../stores/game';

export function ResignButton() {
  const [showConfirm, setShowConfirm] = useState(false);
  const playerNumber = useGameStore((s) => s.playerNumber);
  const status = useGameStore((s) => s.status);
  const isEliminated = useGameStore(selectIsPlayerEliminated);

  // Only show for active players during gameplay who haven't been eliminated
  if (playerNumber === 0 || status !== 'playing' || isEliminated) {
    return null;
  }

  const handleResign = () => {
    useGameStore.getState().resign();
    setShowConfirm(false);
  };

  return (
    <>
      <button className="resign-button" onClick={() => setShowConfirm(true)}>
        Resign
      </button>

      {showConfirm && (
        <div className="resign-confirm-overlay">
          <div className="resign-confirm-modal">
            <p>Are you sure you want to resign?</p>
            <div className="resign-confirm-actions">
              <button className="resign-confirm-yes" onClick={handleResign}>
                Resign
              </button>
              <button className="resign-confirm-no" onClick={() => setShowConfirm(false)}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
