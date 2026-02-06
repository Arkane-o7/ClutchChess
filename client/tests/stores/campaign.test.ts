/**
 * Campaign Store Tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  useCampaignStore,
  BELT_NAMES,
  BELT_COLORS,
  getLevelsForBelt,
  getBeltCompletionCount,
} from '../../src/stores/campaign';
import type { CampaignLevel, CampaignProgress } from '../../src/api/types';

// Mock the API module
vi.mock('../../src/api/client', () => ({
  getCampaignProgress: vi.fn(),
  getCampaignLevels: vi.fn(),
  startCampaignLevel: vi.fn(),
  ApiClientError: class ApiClientError extends Error {
    constructor(
      message: string,
      public status: number,
      public detail?: string
    ) {
      super(message);
    }
  },
}));

import * as api from '../../src/api/client';

const mockProgress: CampaignProgress = {
  levelsCompleted: { '0': true, '1': true },
  beltsCompleted: {},
  currentBelt: 1,
  maxBelt: 4,
};

const mockLevels: CampaignLevel[] = [
  {
    levelId: 0,
    belt: 1,
    beltName: 'White',
    title: 'Welcome to Clutch Chess',
    description: 'First level',
    speed: 'standard',
    playerCount: 2,
    isUnlocked: true,
    isCompleted: true,
  },
  {
    levelId: 1,
    belt: 1,
    beltName: 'White',
    title: 'The Elite Guard',
    description: 'Second level',
    speed: 'standard',
    playerCount: 2,
    isUnlocked: true,
    isCompleted: true,
  },
  {
    levelId: 2,
    belt: 1,
    beltName: 'White',
    title: 'March of the Pawns',
    description: 'Third level',
    speed: 'standard',
    playerCount: 2,
    isUnlocked: true,
    isCompleted: false,
  },
  {
    levelId: 8,
    belt: 2,
    beltName: 'Yellow',
    title: 'Bishop Blockade',
    description: 'Belt 2 level',
    speed: 'standard',
    playerCount: 2,
    isUnlocked: false,
    isCompleted: false,
  },
];

describe('useCampaignStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useCampaignStore.getState().reset();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('initial state', () => {
    it('has correct initial values', () => {
      const state = useCampaignStore.getState();
      expect(state.progress).toBeNull();
      expect(state.levels).toEqual([]);
      expect(state.selectedBelt).toBe(1);
      expect(state.isLoading).toBe(false);
      expect(state.isStartingLevel).toBe(false);
      expect(state.error).toBeNull();
    });
  });

  describe('init', () => {
    it('fetches progress and levels in parallel', async () => {
      vi.mocked(api.getCampaignProgress).mockResolvedValueOnce(mockProgress);
      vi.mocked(api.getCampaignLevels).mockResolvedValueOnce({ levels: mockLevels });

      await useCampaignStore.getState().init();

      const state = useCampaignStore.getState();
      expect(state.progress).toEqual(mockProgress);
      expect(state.levels).toEqual(mockLevels);
      expect(state.selectedBelt).toBe(mockProgress.currentBelt);
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
    });

    it('sets error on failure', async () => {
      vi.mocked(api.getCampaignProgress).mockRejectedValueOnce(new Error('Network error'));
      vi.mocked(api.getCampaignLevels).mockResolvedValueOnce({ levels: mockLevels });

      await useCampaignStore.getState().init();

      const state = useCampaignStore.getState();
      expect(state.progress).toBeNull();
      expect(state.isLoading).toBe(false);
      expect(state.error).toBe('Failed to load campaign data');
    });

    it('sets login error for 401', async () => {
      const error = new api.ApiClientError('Unauthorized', 401);
      vi.mocked(api.getCampaignProgress).mockRejectedValueOnce(error);
      vi.mocked(api.getCampaignLevels).mockResolvedValueOnce({ levels: mockLevels });

      await useCampaignStore.getState().init();

      const state = useCampaignStore.getState();
      expect(state.error).toBe('Please log in to view campaign progress');
    });

    it('guards against concurrent requests', async () => {
      vi.mocked(api.getCampaignProgress).mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve(mockProgress), 100))
      );
      vi.mocked(api.getCampaignLevels).mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve({ levels: mockLevels }), 100))
      );

      // Start first request
      const promise1 = useCampaignStore.getState().init();

      // Second request should be blocked
      useCampaignStore.getState().init();

      await promise1;

      expect(api.getCampaignProgress).toHaveBeenCalledTimes(1);
      expect(api.getCampaignLevels).toHaveBeenCalledTimes(1);
    });
  });

  describe('selectBelt', () => {
    it('updates selected belt', () => {
      useCampaignStore.getState().selectBelt(3);
      expect(useCampaignStore.getState().selectedBelt).toBe(3);
    });
  });

  describe('startLevel', () => {
    it('starts level and returns game info', async () => {
      vi.mocked(api.startCampaignLevel).mockResolvedValueOnce({
        gameId: 'ABC123',
        playerKey: 'key123',
        playerNumber: 1,
      });

      const result = await useCampaignStore.getState().startLevel(0);

      expect(result).toEqual({ gameId: 'ABC123', playerKey: 'key123' });
      expect(useCampaignStore.getState().isStartingLevel).toBe(false);
    });

    it('sets error for locked level (403)', async () => {
      const error = new api.ApiClientError('Forbidden', 403);
      vi.mocked(api.startCampaignLevel).mockRejectedValueOnce(error);

      await expect(useCampaignStore.getState().startLevel(5)).rejects.toThrow();

      expect(useCampaignStore.getState().error).toBe('This level is locked');
    });

    it('sets error for unauthenticated (401)', async () => {
      const error = new api.ApiClientError('Unauthorized', 401);
      vi.mocked(api.startCampaignLevel).mockRejectedValueOnce(error);

      await expect(useCampaignStore.getState().startLevel(0)).rejects.toThrow();

      expect(useCampaignStore.getState().error).toBe('Please log in to play campaign');
    });

    it('guards against concurrent requests', async () => {
      vi.mocked(api.startCampaignLevel).mockImplementation(
        () =>
          new Promise((resolve) =>
            setTimeout(
              () => resolve({ gameId: 'ABC', playerKey: 'key', playerNumber: 1 }),
              100
            )
          )
      );

      // Start first request
      const promise1 = useCampaignStore.getState().startLevel(0);

      // Second request should throw
      await expect(useCampaignStore.getState().startLevel(0)).rejects.toThrow(
        'Already starting a level'
      );

      await promise1;
      expect(api.startCampaignLevel).toHaveBeenCalledTimes(1);
    });
  });

  describe('clearError', () => {
    it('clears error', () => {
      useCampaignStore.setState({ error: 'Some error' });
      useCampaignStore.getState().clearError();
      expect(useCampaignStore.getState().error).toBeNull();
    });
  });

  describe('reset', () => {
    it('resets to initial state', () => {
      useCampaignStore.setState({
        progress: mockProgress,
        levels: mockLevels,
        selectedBelt: 3,
        error: 'error',
      });

      useCampaignStore.getState().reset();

      const state = useCampaignStore.getState();
      expect(state.progress).toBeNull();
      expect(state.levels).toEqual([]);
      expect(state.selectedBelt).toBe(1);
      expect(state.error).toBeNull();
    });
  });
});

describe('BELT_NAMES', () => {
  it('has correct belt names', () => {
    expect(BELT_NAMES[1]).toBe('White');
    expect(BELT_NAMES[2]).toBe('Yellow');
    expect(BELT_NAMES[3]).toBe('Green');
    expect(BELT_NAMES[4]).toBe('Purple');
  });
});

describe('BELT_COLORS', () => {
  it('has colors for each belt', () => {
    expect(BELT_COLORS[1]).toBe('#ffffff');
    expect(BELT_COLORS[2]).toBe('#ffd700');
    expect(BELT_COLORS[3]).toBe('#22c55e');
    expect(BELT_COLORS[4]).toBe('#a855f7');
  });
});

describe('getLevelsForBelt', () => {
  it('returns levels for specified belt', () => {
    const belt1Levels = getLevelsForBelt(mockLevels, 1);
    expect(belt1Levels).toHaveLength(3);
    expect(belt1Levels.every((l) => l.belt === 1)).toBe(true);
  });

  it('returns empty array for belt with no levels', () => {
    const belt5Levels = getLevelsForBelt(mockLevels, 5);
    expect(belt5Levels).toEqual([]);
  });
});

describe('getBeltCompletionCount', () => {
  it('counts completed levels in belt', () => {
    const count = getBeltCompletionCount(mockLevels, 1);
    expect(count).toBe(2); // levelId 0 and 1 are completed
  });

  it('returns 0 for belt with no completed levels', () => {
    const count = getBeltCompletionCount(mockLevels, 2);
    expect(count).toBe(0);
  });
});
