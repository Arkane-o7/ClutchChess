/**
 * Tests for the game store - focusing on rating update handling
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useGameStore, selectIsPlayerEliminated } from '../../src/stores/game';
import type { RatingUpdateMessage } from '../../src/ws/types';

// ============================================
// Test Fixtures
// ============================================

const createRatingUpdateMessage = (
  ratings: Record<string, { old_rating: number; new_rating: number; old_belt: string; new_belt: string; belt_changed: boolean }>
): RatingUpdateMessage => ({
  type: 'rating_update',
  ratings,
});

// ============================================
// Tests
// ============================================

describe('Game Store', () => {
  beforeEach(() => {
    // Reset store state before each test
    useGameStore.getState().reset();
  });

  describe('initial state', () => {
    it('has null ratingChange by default', () => {
      const state = useGameStore.getState();
      expect(state.ratingChange).toBeNull();
    });
  });

  describe('handleRatingUpdate', () => {
    it('sets ratingChange for the current player', () => {
      // Set player number to 1
      useGameStore.setState({ playerNumber: 1 });

      const message = createRatingUpdateMessage({
        '1': {
          old_rating: 1200,
          new_rating: 1215,
          old_belt: 'green',
          new_belt: 'green',
          belt_changed: false,
        },
        '2': {
          old_rating: 1180,
          new_rating: 1165,
          old_belt: 'green',
          new_belt: 'green',
          belt_changed: false,
        },
      });

      useGameStore.getState().handleRatingUpdate(message);

      const state = useGameStore.getState();
      expect(state.ratingChange).toEqual({
        oldRating: 1200,
        newRating: 1215,
        oldBelt: 'green',
        newBelt: 'green',
        beltChanged: false,
      });
    });

    it('sets ratingChange for player 2', () => {
      // Set player number to 2
      useGameStore.setState({ playerNumber: 2 });

      const message = createRatingUpdateMessage({
        '1': {
          old_rating: 1200,
          new_rating: 1215,
          old_belt: 'green',
          new_belt: 'green',
          belt_changed: false,
        },
        '2': {
          old_rating: 1180,
          new_rating: 1165,
          old_belt: 'green',
          new_belt: 'green',
          belt_changed: false,
        },
      });

      useGameStore.getState().handleRatingUpdate(message);

      const state = useGameStore.getState();
      expect(state.ratingChange).toEqual({
        oldRating: 1180,
        newRating: 1165,
        oldBelt: 'green',
        newBelt: 'green',
        beltChanged: false,
      });
    });

    it('does not set ratingChange for spectators (playerNumber 0)', () => {
      // Set player number to 0 (spectator)
      useGameStore.setState({ playerNumber: 0 });

      const message = createRatingUpdateMessage({
        '1': {
          old_rating: 1200,
          new_rating: 1215,
          old_belt: 'green',
          new_belt: 'green',
          belt_changed: false,
        },
        '2': {
          old_rating: 1180,
          new_rating: 1165,
          old_belt: 'green',
          new_belt: 'green',
          belt_changed: false,
        },
      });

      useGameStore.getState().handleRatingUpdate(message);

      const state = useGameStore.getState();
      // Spectators won't have their player number (0) in ratings
      expect(state.ratingChange).toBeNull();
    });

    it('correctly transforms snake_case to camelCase', () => {
      useGameStore.setState({ playerNumber: 1 });

      const message = createRatingUpdateMessage({
        '1': {
          old_rating: 1100,
          new_rating: 1132,
          old_belt: 'green',
          new_belt: 'purple',
          belt_changed: true,
        },
      });

      useGameStore.getState().handleRatingUpdate(message);

      const state = useGameStore.getState();
      expect(state.ratingChange).toEqual({
        oldRating: 1100,
        newRating: 1132,
        oldBelt: 'green',
        newBelt: 'purple',
        beltChanged: true,
      });
    });

    it('handles missing player key in ratings gracefully', () => {
      useGameStore.setState({ playerNumber: 3 });

      const message = createRatingUpdateMessage({
        '1': {
          old_rating: 1200,
          new_rating: 1215,
          old_belt: 'green',
          new_belt: 'green',
          belt_changed: false,
        },
        '2': {
          old_rating: 1180,
          new_rating: 1165,
          old_belt: 'green',
          new_belt: 'green',
          belt_changed: false,
        },
      });

      // Should not throw
      useGameStore.getState().handleRatingUpdate(message);

      const state = useGameStore.getState();
      expect(state.ratingChange).toBeNull();
    });

    it('handles belt promotion correctly', () => {
      useGameStore.setState({ playerNumber: 1 });

      const message = createRatingUpdateMessage({
        '1': {
          old_rating: 1290,
          new_rating: 1310,
          old_belt: 'green',
          new_belt: 'purple',
          belt_changed: true,
        },
      });

      useGameStore.getState().handleRatingUpdate(message);

      const state = useGameStore.getState();
      expect(state.ratingChange?.beltChanged).toBe(true);
      expect(state.ratingChange?.oldBelt).toBe('green');
      expect(state.ratingChange?.newBelt).toBe('purple');
    });

    it('handles belt demotion correctly', () => {
      useGameStore.setState({ playerNumber: 1 });

      const message = createRatingUpdateMessage({
        '1': {
          old_rating: 1105,
          new_rating: 1085,
          old_belt: 'green',
          new_belt: 'yellow',
          belt_changed: true,
        },
      });

      useGameStore.getState().handleRatingUpdate(message);

      const state = useGameStore.getState();
      expect(state.ratingChange?.beltChanged).toBe(true);
      expect(state.ratingChange?.oldBelt).toBe('green');
      expect(state.ratingChange?.newBelt).toBe('yellow');
    });
  });

  describe('resign', () => {
    it('does nothing when no wsClient', () => {
      useGameStore.setState({ status: 'playing', wsClient: null });
      // Should not throw
      useGameStore.getState().resign();
    });

    it('does nothing when game is not playing', () => {
      const mockSendResign = vi.fn();
      useGameStore.setState({
        status: 'waiting',
        wsClient: { sendResign: mockSendResign, disconnect: vi.fn() } as unknown as ReturnType<typeof useGameStore.getState>['wsClient'],
      });
      useGameStore.getState().resign();
      expect(mockSendResign).not.toHaveBeenCalled();
    });

    it('sends resign message when playing', () => {
      const mockSendResign = vi.fn();
      useGameStore.setState({
        status: 'playing',
        wsClient: { sendResign: mockSendResign, disconnect: vi.fn() } as unknown as ReturnType<typeof useGameStore.getState>['wsClient'],
      });
      useGameStore.getState().resign();
      expect(mockSendResign).toHaveBeenCalledOnce();
    });
  });

  describe('selectIsPlayerEliminated', () => {
    it('returns false for spectators', () => {
      useGameStore.setState({ playerNumber: 0, pieces: [] });
      expect(selectIsPlayerEliminated(useGameStore.getState())).toBe(false);
    });

    it('returns false when king is alive', () => {
      useGameStore.setState({
        playerNumber: 1,
        pieces: [{ id: 'K:1:7:4', type: 'K', player: 1, row: 7, col: 4, captured: false, moving: false, onCooldown: false, moved: false }],
      });
      expect(selectIsPlayerEliminated(useGameStore.getState())).toBe(false);
    });

    it('returns true when king is captured', () => {
      useGameStore.setState({
        playerNumber: 1,
        pieces: [{ id: 'K:1:7:4', type: 'K', player: 1, row: 7, col: 4, captured: true, moving: false, onCooldown: false, moved: false }],
      });
      expect(selectIsPlayerEliminated(useGameStore.getState())).toBe(true);
    });
  });

  describe('reset', () => {
    it('clears ratingChange on reset', () => {
      useGameStore.setState({
        playerNumber: 1,
        ratingChange: {
          oldRating: 1200,
          newRating: 1215,
          oldBelt: 'green',
          newBelt: 'green',
          beltChanged: false,
        },
      });

      useGameStore.getState().reset();

      const state = useGameStore.getState();
      expect(state.ratingChange).toBeNull();
    });
  });
});
