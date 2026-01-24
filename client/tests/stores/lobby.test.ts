import { describe, it, expect, beforeEach } from 'vitest';
import {
  useLobbyStore,
  selectIsHost,
  selectMyPlayer,
  selectIsAllReady,
  selectIsFull,
  selectCanStart,
} from '../../src/stores/lobby';
import type { Lobby, LobbyPlayer, LobbySettings } from '../../src/api/types';

// Partial state type for selector tests
type PartialLobbyState = {
  mySlot?: number | null;
  lobby?: Lobby | null;
};

// ============================================
// Test Fixtures
// ============================================

const createMockSettings = (overrides?: Partial<LobbySettings>): LobbySettings => ({
  isPublic: true,
  speed: 'standard',
  playerCount: 2,
  isRanked: false,
  ...overrides,
});

const createMockPlayer = (slot: number, overrides?: Partial<LobbyPlayer>): LobbyPlayer => ({
  slot,
  userId: null,
  username: `Player ${slot}`,
  isAi: false,
  aiType: null,
  isReady: false,
  ...overrides,
});

const createMockLobby = (overrides?: Partial<Lobby>): Lobby => ({
  id: 1,
  code: 'ABC123',
  hostSlot: 1,
  settings: createMockSettings(),
  players: {
    1: createMockPlayer(1),
  },
  status: 'waiting',
  currentGameId: null,
  gamesPlayed: 0,
  ...overrides,
});

// ============================================
// Selector Tests
// ============================================

describe('Lobby Selectors', () => {
  describe('selectIsHost', () => {
    it('returns true when mySlot matches hostSlot', () => {
      const state: PartialLobbyState = {
        mySlot: 1,
        lobby: createMockLobby({ hostSlot: 1 }),
      };
      expect(selectIsHost(state as Parameters<typeof selectIsHost>[0])).toBe(true);
    });

    it('returns false when mySlot does not match hostSlot', () => {
      const state: PartialLobbyState = {
        mySlot: 2,
        lobby: createMockLobby({ hostSlot: 1 }),
      };
      expect(selectIsHost(state as Parameters<typeof selectIsHost>[0])).toBe(false);
    });

    it('returns false when mySlot is null', () => {
      const state: PartialLobbyState = {
        mySlot: null,
        lobby: createMockLobby({ hostSlot: 1 }),
      };
      expect(selectIsHost(state as Parameters<typeof selectIsHost>[0])).toBe(false);
    });

    it('returns false when lobby is null', () => {
      const state: PartialLobbyState = {
        mySlot: 1,
        lobby: null,
      };
      expect(selectIsHost(state as Parameters<typeof selectIsHost>[0])).toBe(false);
    });
  });

  describe('selectMyPlayer', () => {
    it('returns the player when mySlot exists in players', () => {
      const player = createMockPlayer(1, { username: 'TestPlayer' });
      const state: PartialLobbyState = {
        mySlot: 1,
        lobby: createMockLobby({ players: { 1: player } }),
      };
      expect(selectMyPlayer(state as Parameters<typeof selectMyPlayer>[0])).toEqual(player);
    });

    it('returns null when mySlot is null', () => {
      const state: PartialLobbyState = {
        mySlot: null,
        lobby: createMockLobby(),
      };
      expect(selectMyPlayer(state as Parameters<typeof selectMyPlayer>[0])).toBeNull();
    });

    it('returns null when player not in lobby', () => {
      const state: PartialLobbyState = {
        mySlot: 2,
        lobby: createMockLobby({ players: { 1: createMockPlayer(1) } }),
      };
      expect(selectMyPlayer(state as Parameters<typeof selectMyPlayer>[0])).toBeNull();
    });
  });

  describe('selectIsAllReady', () => {
    it('returns true when all players are ready and lobby is full', () => {
      const state: PartialLobbyState = {
        lobby: createMockLobby({
          settings: createMockSettings({ playerCount: 2 }),
          players: {
            1: createMockPlayer(1, { isReady: true }),
            2: createMockPlayer(2, { isReady: true }),
          },
        }),
      };
      expect(selectIsAllReady(state as Parameters<typeof selectIsAllReady>[0])).toBe(true);
    });

    it('returns false when not all players are ready', () => {
      const state: PartialLobbyState = {
        lobby: createMockLobby({
          settings: createMockSettings({ playerCount: 2 }),
          players: {
            1: createMockPlayer(1, { isReady: true }),
            2: createMockPlayer(2, { isReady: false }),
          },
        }),
      };
      expect(selectIsAllReady(state as Parameters<typeof selectIsAllReady>[0])).toBe(false);
    });

    it('returns false when lobby is not full', () => {
      const state: PartialLobbyState = {
        lobby: createMockLobby({
          settings: createMockSettings({ playerCount: 2 }),
          players: {
            1: createMockPlayer(1, { isReady: true }),
          },
        }),
      };
      expect(selectIsAllReady(state as Parameters<typeof selectIsAllReady>[0])).toBe(false);
    });

    it('returns false when lobby is null', () => {
      const state: PartialLobbyState = { lobby: null };
      expect(selectIsAllReady(state as Parameters<typeof selectIsAllReady>[0])).toBe(false);
    });
  });

  describe('selectIsFull', () => {
    it('returns true when player count matches settings', () => {
      const state: PartialLobbyState = {
        lobby: createMockLobby({
          settings: createMockSettings({ playerCount: 2 }),
          players: {
            1: createMockPlayer(1),
            2: createMockPlayer(2),
          },
        }),
      };
      expect(selectIsFull(state as Parameters<typeof selectIsFull>[0])).toBe(true);
    });

    it('returns false when player count is less than settings', () => {
      const state: PartialLobbyState = {
        lobby: createMockLobby({
          settings: createMockSettings({ playerCount: 2 }),
          players: {
            1: createMockPlayer(1),
          },
        }),
      };
      expect(selectIsFull(state as Parameters<typeof selectIsFull>[0])).toBe(false);
    });

    it('returns false when lobby is null', () => {
      const state: PartialLobbyState = { lobby: null };
      expect(selectIsFull(state as Parameters<typeof selectIsFull>[0])).toBe(false);
    });
  });

  describe('selectCanStart', () => {
    it('returns true when host, all ready, and full', () => {
      const state: PartialLobbyState = {
        mySlot: 1,
        lobby: createMockLobby({
          hostSlot: 1,
          settings: createMockSettings({ playerCount: 2 }),
          players: {
            1: createMockPlayer(1, { isReady: true }),
            2: createMockPlayer(2, { isReady: true }),
          },
        }),
      };
      expect(selectCanStart(state as Parameters<typeof selectCanStart>[0])).toBe(true);
    });

    it('returns false when not host', () => {
      const state: PartialLobbyState = {
        mySlot: 2,
        lobby: createMockLobby({
          hostSlot: 1,
          settings: createMockSettings({ playerCount: 2 }),
          players: {
            1: createMockPlayer(1, { isReady: true }),
            2: createMockPlayer(2, { isReady: true }),
          },
        }),
      };
      expect(selectCanStart(state as Parameters<typeof selectCanStart>[0])).toBe(false);
    });

    it('returns false when not all ready', () => {
      const state: PartialLobbyState = {
        mySlot: 1,
        lobby: createMockLobby({
          hostSlot: 1,
          settings: createMockSettings({ playerCount: 2 }),
          players: {
            1: createMockPlayer(1, { isReady: true }),
            2: createMockPlayer(2, { isReady: false }),
          },
        }),
      };
      expect(selectCanStart(state as Parameters<typeof selectCanStart>[0])).toBe(false);
    });

    it('returns false when not full', () => {
      const state: PartialLobbyState = {
        mySlot: 1,
        lobby: createMockLobby({
          hostSlot: 1,
          settings: createMockSettings({ playerCount: 2 }),
          players: {
            1: createMockPlayer(1, { isReady: true }),
          },
        }),
      };
      expect(selectCanStart(state as Parameters<typeof selectCanStart>[0])).toBe(false);
    });
  });
});

// ============================================
// Store State Tests
// ============================================

describe('useLobbyStore', () => {
  beforeEach(() => {
    // Reset store between tests
    useLobbyStore.getState().reset();
  });

  describe('initial state', () => {
    it('has correct initial values', () => {
      const state = useLobbyStore.getState();
      expect(state.code).toBeNull();
      expect(state.playerKey).toBeNull();
      expect(state.mySlot).toBeNull();
      expect(state.connectionState).toBe('disconnected');
      expect(state.error).toBeNull();
      expect(state.lobby).toBeNull();
      expect(state.publicLobbies).toEqual([]);
      expect(state.pendingGameId).toBeNull();
    });
  });

  describe('clearError', () => {
    it('clears the error state', () => {
      useLobbyStore.setState({ error: 'Some error' });
      useLobbyStore.getState().clearError();
      expect(useLobbyStore.getState().error).toBeNull();
    });
  });

  describe('clearPendingGame', () => {
    it('clears pending game info', () => {
      useLobbyStore.setState({
        pendingGameId: 'game123',
        pendingGamePlayerKey: 'key123',
      });
      useLobbyStore.getState().clearPendingGame();
      const state = useLobbyStore.getState();
      expect(state.pendingGameId).toBeNull();
      expect(state.pendingGamePlayerKey).toBeNull();
    });
  });

  describe('reset', () => {
    it('resets all state to initial values', () => {
      useLobbyStore.setState({
        code: 'ABC123',
        playerKey: 'key123',
        mySlot: 1,
        error: 'Some error',
        lobby: createMockLobby(),
        pendingGameId: 'game123',
      });

      useLobbyStore.getState().reset();
      const state = useLobbyStore.getState();

      expect(state.code).toBeNull();
      expect(state.playerKey).toBeNull();
      expect(state.mySlot).toBeNull();
      expect(state.error).toBeNull();
      expect(state.lobby).toBeNull();
      expect(state.pendingGameId).toBeNull();
    });
  });
});

// ============================================
// Message Handler Tests
// ============================================

describe('Message Handlers', () => {
  beforeEach(() => {
    useLobbyStore.getState().reset();
  });

  // Helper to simulate receiving a WebSocket message
  const simulateMessage = (data: object) => {
    const event = { data: JSON.stringify(data) } as MessageEvent;
    useLobbyStore.getState()._handleMessage(event);
  };

  describe('lobby_state', () => {
    it('sets lobby from message', () => {
      const lobby = createMockLobby();
      simulateMessage({ type: 'lobby_state', lobby });
      expect(useLobbyStore.getState().lobby).toEqual(lobby);
    });

    it('clears error when receiving lobby state', () => {
      useLobbyStore.setState({ error: 'Previous error' });
      simulateMessage({ type: 'lobby_state', lobby: createMockLobby() });
      expect(useLobbyStore.getState().error).toBeNull();
    });
  });

  describe('player_joined', () => {
    it('adds new player to lobby', () => {
      useLobbyStore.setState({ lobby: createMockLobby() });
      const newPlayer = createMockPlayer(2, { username: 'NewPlayer' });
      simulateMessage({ type: 'player_joined', slot: 2, player: newPlayer });

      const lobby = useLobbyStore.getState().lobby;
      expect(lobby?.players[2]).toEqual(newPlayer);
    });

    it('does nothing if lobby is null', () => {
      useLobbyStore.setState({ lobby: null });
      const newPlayer = createMockPlayer(2);
      simulateMessage({ type: 'player_joined', slot: 2, player: newPlayer });
      expect(useLobbyStore.getState().lobby).toBeNull();
    });
  });

  describe('player_left', () => {
    it('removes player from lobby', () => {
      useLobbyStore.setState({
        lobby: createMockLobby({
          players: {
            1: createMockPlayer(1),
            2: createMockPlayer(2),
          },
        }),
      });
      simulateMessage({ type: 'player_left', slot: 2, reason: 'left' });

      const lobby = useLobbyStore.getState().lobby;
      expect(lobby?.players[2]).toBeUndefined();
      expect(lobby?.players[1]).toBeDefined();
    });
  });

  describe('player_ready', () => {
    it('updates player ready state', () => {
      useLobbyStore.setState({
        lobby: createMockLobby({
          players: { 1: createMockPlayer(1, { isReady: false }) },
        }),
      });
      simulateMessage({ type: 'player_ready', slot: 1, ready: true });

      const lobby = useLobbyStore.getState().lobby;
      expect(lobby?.players[1].isReady).toBe(true);
    });

    it('does nothing for non-existent player', () => {
      useLobbyStore.setState({ lobby: createMockLobby() });
      simulateMessage({ type: 'player_ready', slot: 99, ready: true });
      // Should not throw, just no-op
      expect(useLobbyStore.getState().lobby?.players[99]).toBeUndefined();
    });
  });

  describe('settings_updated', () => {
    it('updates lobby settings', () => {
      useLobbyStore.setState({ lobby: createMockLobby() });
      const newSettings = createMockSettings({ speed: 'lightning', playerCount: 4 });
      simulateMessage({ type: 'settings_updated', settings: newSettings });

      const lobby = useLobbyStore.getState().lobby;
      expect(lobby?.settings.speed).toBe('lightning');
      expect(lobby?.settings.playerCount).toBe(4);
    });
  });

  describe('host_changed', () => {
    it('updates host slot', () => {
      useLobbyStore.setState({
        lobby: createMockLobby({ hostSlot: 1 }),
      });
      simulateMessage({ type: 'host_changed', newHostSlot: 2 });

      expect(useLobbyStore.getState().lobby?.hostSlot).toBe(2);
    });
  });

  describe('game_starting', () => {
    it('updates lobby status and stores game info', () => {
      useLobbyStore.setState({
        lobby: createMockLobby({ status: 'waiting' }),
      });
      simulateMessage({
        type: 'game_starting',
        gameId: 'game123',
        playerKey: 'key123',
        lobbyCode: 'ABC123',
      });

      const state = useLobbyStore.getState();
      expect(state.lobby?.status).toBe('in_game');
      expect(state.lobby?.currentGameId).toBe('game123');
      expect(state.pendingGameId).toBe('game123');
      expect(state.pendingGamePlayerKey).toBe('key123');
    });

    it('preserves lobbyCode in state', () => {
      useLobbyStore.setState({
        code: null, // Simulate code being lost
        lobby: createMockLobby(),
      });
      simulateMessage({
        type: 'game_starting',
        gameId: 'game123',
        playerKey: 'key123',
        lobbyCode: 'XYZ789',
      });

      expect(useLobbyStore.getState().code).toBe('XYZ789');
    });
  });

  describe('game_ended', () => {
    it('updates lobby status and increments games played', () => {
      useLobbyStore.setState({
        lobby: createMockLobby({ status: 'in_game', gamesPlayed: 2 }),
      });
      simulateMessage({ type: 'game_ended', winner: 1, winReason: 'checkmate' });

      const lobby = useLobbyStore.getState().lobby;
      expect(lobby?.status).toBe('finished');
      expect(lobby?.gamesPlayed).toBe(3);
    });
  });

  describe('error', () => {
    it('stores error message', () => {
      simulateMessage({ type: 'error', message: 'Something went wrong' });
      expect(useLobbyStore.getState().error).toBe('Something went wrong');
    });
  });

  describe('invalid message', () => {
    it('handles malformed JSON gracefully', () => {
      const event = { data: 'not json' } as MessageEvent;
      // Should not throw
      useLobbyStore.getState()._handleMessage(event);
      // State should be unchanged
      expect(useLobbyStore.getState().lobby).toBeNull();
    });
  });
});
