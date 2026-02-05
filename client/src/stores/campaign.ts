/**
 * Campaign Store - State management for campaign mode
 *
 * Manages campaign progress, level listing, and game creation.
 */

import { create } from 'zustand';
import * as api from '../api/client';
import type { CampaignLevel, CampaignProgress } from '../api/types';

/**
 * Belt names by belt number (1-indexed)
 * Must match server-side BELT_NAMES
 */
export const BELT_NAMES: Record<number, string> = {
  1: 'White',
  2: 'Yellow',
  3: 'Green',
  4: 'Purple',
  5: 'Orange',
  6: 'Blue',
  7: 'Brown',
  8: 'Red',
  9: 'Black',
};

/**
 * Belt colors for styling (CSS color values)
 */
export const BELT_COLORS: Record<number, string> = {
  1: '#ffffff',
  2: '#ffd700',
  3: '#22c55e',
  4: '#a855f7',
  5: '#f97316',
  6: '#3b82f6',
  7: '#92400e',
  8: '#ef4444',
  9: '#000000',
};

interface CampaignState {
  // Data
  progress: CampaignProgress | null;
  levels: CampaignLevel[];
  selectedBelt: number;

  // UI state
  isLoading: boolean;
  isStartingLevel: boolean;
  error: string | null;

  // Actions
  init: () => Promise<void>;
  selectBelt: (belt: number) => void;
  startLevel: (levelId: number) => Promise<{ gameId: string; playerKey: string }>;
  clearError: () => void;
  reset: () => void;
}

const initialState = {
  progress: null,
  levels: [],
  selectedBelt: 1,
  isLoading: false,
  isStartingLevel: false,
  error: null,
};

export const useCampaignStore = create<CampaignState>((set, get) => ({
  ...initialState,

  init: async () => {
    // Guard against concurrent requests
    if (get().isLoading) return;

    set({ isLoading: true, error: null });
    try {
      // Fetch progress and levels in parallel
      const [progress, levelsResponse] = await Promise.all([
        api.getCampaignProgress(),
        api.getCampaignLevels(),
      ]);
      set({
        progress,
        levels: levelsResponse.levels,
        selectedBelt: progress.currentBelt,
        isLoading: false,
      });
    } catch (error) {
      const message =
        error instanceof api.ApiClientError && error.status === 401
          ? 'Please log in to view campaign progress'
          : 'Failed to load campaign data';
      set({ error: message, isLoading: false });
    }
  },

  selectBelt: (belt: number) => {
    set({ selectedBelt: belt });
  },

  startLevel: async (levelId: number) => {
    // Guard against concurrent requests
    if (get().isStartingLevel) {
      throw new Error('Already starting a level');
    }

    set({ isStartingLevel: true, error: null });
    try {
      const response = await api.startCampaignLevel(levelId);
      set({ isStartingLevel: false });
      return {
        gameId: response.gameId,
        playerKey: response.playerKey,
      };
    } catch (error) {
      let message = 'Failed to start level';
      if (error instanceof api.ApiClientError) {
        if (error.status === 401) {
          message = 'Please log in to play campaign';
        } else if (error.status === 403) {
          message = 'This level is locked';
        } else if (error.detail) {
          message = error.detail;
        }
      }
      set({ error: message, isStartingLevel: false });
      throw error;
    }
  },

  clearError: () => set({ error: null }),

  reset: () => set(initialState),
}));

// Selectors for optimized re-renders
export const selectProgress = (state: CampaignState) => state.progress;
export const selectLevels = (state: CampaignState) => state.levels;
export const selectSelectedBelt = (state: CampaignState) => state.selectedBelt;
export const selectIsLoading = (state: CampaignState) => state.isLoading;
export const selectError = (state: CampaignState) => state.error;

/**
 * Get levels for a specific belt
 */
export function getLevelsForBelt(levels: CampaignLevel[], belt: number): CampaignLevel[] {
  return levels.filter((level) => level.belt === belt);
}

/**
 * Get completion count for a belt
 */
export function getBeltCompletionCount(levels: CampaignLevel[], belt: number): number {
  return levels.filter((level) => level.belt === belt && level.isCompleted).length;
}
