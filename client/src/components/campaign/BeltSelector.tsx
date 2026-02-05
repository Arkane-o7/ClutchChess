/**
 * BeltSelector - Component for selecting campaign belts
 *
 * Shows all available belts with completion status and allows selection.
 */

import { useCallback } from 'react';
import { BELT_NAMES, BELT_COLORS } from '../../stores/campaign';
import './BeltSelector.css';

interface BeltSelectorProps {
  currentBelt: number;
  maxBelt: number;
  selectedBelt: number;
  beltsCompleted: Record<string, boolean>;
  onSelectBelt: (belt: number) => void;
}

function BeltSelector({
  currentBelt,
  maxBelt,
  selectedBelt,
  beltsCompleted,
  onSelectBelt,
}: BeltSelectorProps) {
  const handleBeltClick = useCallback(
    (belt: number) => {
      if (belt <= currentBelt) {
        onSelectBelt(belt);
      }
    },
    [currentBelt, onSelectBelt]
  );

  // Show belts 1 through maxBelt
  const belts = Array.from({ length: maxBelt }, (_, i) => i + 1);

  return (
    <div className="belt-selector">
      <div className="belt-selector-list">
        {belts.map((belt) => {
          const isUnlocked = belt <= currentBelt;
          const isCompleted = beltsCompleted[String(belt)] === true;
          const isSelected = belt === selectedBelt;

          return (
            <button
              key={belt}
              className={`belt-selector-item ${isSelected ? 'selected' : ''} ${
                !isUnlocked ? 'locked' : ''
              } ${isCompleted ? 'completed' : ''}`}
              onClick={() => handleBeltClick(belt)}
              disabled={!isUnlocked}
              aria-label={`${BELT_NAMES[belt]} Belt${isCompleted ? ' (Completed)' : ''}${
                !isUnlocked ? ' (Locked)' : ''
              }`}
            >
              <div
                className="belt-selector-color"
                style={{
                  backgroundColor: BELT_COLORS[belt],
                  borderColor: belt === 1 ? '#666' : BELT_COLORS[belt],
                }}
              />
              <span className="belt-selector-name">{BELT_NAMES[belt]}</span>
              {isCompleted && <span className="belt-selector-check">&#10003;</span>}
              {!isUnlocked && <span className="belt-selector-lock">&#128274;</span>}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default BeltSelector;
