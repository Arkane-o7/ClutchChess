/**
 * Game Store - Zustand state management for the game
 *
 * Manages game state, WebSocket connection, and player actions.
 */

import { create } from 'zustand';
import * as api from '../api';
import type { ApiPiece, ApiActiveMove, ApiCooldown, CreateGameRequest } from '../api/types';
import { GameWebSocketClient } from '../ws/client';
import type {
  ConnectionState,
  StateUpdateMessage,
  GameStartedMessage,
  GameOverMessage,
  MoveRejectedMessage,
  WsPieceState,
} from '../ws/types';

// ============================================
// Types
// ============================================

export type PieceType = 'P' | 'N' | 'B' | 'R' | 'Q' | 'K';

export interface Piece {
  id: string;
  type: PieceType;
  player: number;
  row: number;
  col: number;
  captured: boolean;
  moving: boolean;
  onCooldown: boolean;
}

export interface ActiveMove {
  pieceId: string;
  path: [number, number][];
  startTick: number;
  progress: number;
}

export interface Cooldown {
  pieceId: string;
  remainingTicks: number;
}

export interface LegalMove {
  pieceId: string;
  targets: [number, number][];
}

export type GameStatus = 'waiting' | 'playing' | 'finished';
export type BoardType = 'standard' | 'four_player';

interface GameState {
  // Connection state
  gameId: string | null;
  playerKey: string | null;
  playerNumber: number; // 0 = spectator, 1-4 = player
  connectionState: ConnectionState;
  boardType: BoardType;

  // Game state (from server)
  status: GameStatus;
  currentTick: number;
  winner: number | null;
  winReason: string | null;
  pieces: Piece[];
  activeMoves: ActiveMove[];
  cooldowns: Cooldown[];

  // UI state
  selectedPieceId: string | null;
  legalMoves: LegalMove[];
  lastError: string | null;

  // Internal
  wsClient: GameWebSocketClient | null;
}

interface GameActions {
  // Game lifecycle
  createGame: (options: CreateGameRequest) => Promise<void>;
  joinGame: (gameId: string, playerKey?: string) => Promise<void>;
  connect: () => void;
  disconnect: () => void;
  markReady: () => void;
  resyncState: () => Promise<void>;

  // Gameplay
  selectPiece: (pieceId: string | null) => void;
  makeMove: (toRow: number, toCol: number) => void;
  fetchLegalMoves: () => Promise<void>;

  // Internal updates
  updateFromStateMessage: (msg: StateUpdateMessage) => void;
  handleGameStarted: (msg: GameStartedMessage) => void;
  handleGameOver: (msg: GameOverMessage) => void;
  handleMoveRejected: (msg: MoveRejectedMessage) => void;
  setConnectionState: (state: ConnectionState) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

type GameStore = GameState & GameActions;

// ============================================
// Initial State
// ============================================

const initialState: GameState = {
  gameId: null,
  playerKey: null,
  playerNumber: 0,
  connectionState: 'disconnected',
  boardType: 'standard',
  status: 'waiting',
  currentTick: 0,
  winner: null,
  winReason: null,
  pieces: [],
  activeMoves: [],
  cooldowns: [],
  selectedPieceId: null,
  legalMoves: [],
  lastError: null,
  wsClient: null,
};

// ============================================
// Helper Functions
// ============================================

function convertApiPiece(p: ApiPiece): Piece {
  return {
    id: p.id,
    type: p.type,
    player: p.player,
    row: p.row,
    col: p.col,
    captured: p.captured,
    moving: p.moving,
    onCooldown: p.on_cooldown,
  };
}

function convertApiActiveMove(m: ApiActiveMove): ActiveMove {
  return {
    pieceId: m.piece_id,
    path: m.path,
    startTick: m.start_tick,
    progress: m.progress,
  };
}

function convertApiCooldown(c: ApiCooldown): Cooldown {
  return {
    pieceId: c.piece_id,
    remainingTicks: c.remaining_ticks,
  };
}

function mergePieceUpdates(existing: Piece[], updates: WsPieceState[]): Piece[] {
  // Create a map of updates by ID
  const updateMap = new Map(updates.map((u) => [u.id, u]));

  // Update existing pieces
  return existing.map((piece) => {
    const update = updateMap.get(piece.id);
    if (!update) {
      return piece;
    }

    return {
      ...piece,
      row: update.row,
      col: update.col,
      captured: update.captured,
      type: update.type ?? piece.type,
      player: update.player ?? piece.player,
      moving: update.moving ?? piece.moving,
      onCooldown: update.on_cooldown ?? piece.onCooldown,
    };
  });
}

// ============================================
// Store
// ============================================

export const useGameStore = create<GameStore>((set, get) => ({
  ...initialState,

  createGame: async (options) => {
    try {
      const response = await api.createGame(options);

      set({
        gameId: response.game_id,
        playerKey: response.player_key,
        playerNumber: response.player_number,
        boardType: response.board_type,
        status: 'waiting',
        lastError: null,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to create game';
      set({ lastError: message });
      throw error;
    }
  },

  joinGame: async (gameId, playerKey) => {
    try {
      // Fetch initial game state
      const gameState = await api.getGameState(gameId);

      set({
        gameId,
        playerKey: playerKey ?? null,
        playerNumber: playerKey ? 1 : 0, // Will be determined by server
        boardType: gameState.board.board_type,
        status: gameState.status,
        currentTick: gameState.current_tick,
        winner: gameState.winner,
        pieces: gameState.board.pieces.map(convertApiPiece),
        activeMoves: gameState.active_moves.map(convertApiActiveMove),
        cooldowns: gameState.cooldowns.map(convertApiCooldown),
        lastError: null,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to join game';
      set({ lastError: message });
      throw error;
    }
  },

  connect: () => {
    const { gameId, playerKey, wsClient } = get();

    if (!gameId) {
      console.warn('Cannot connect: no gameId');
      return;
    }

    // Disconnect existing client if any
    if (wsClient) {
      wsClient.disconnect();
    }

    // Create new WebSocket client
    const client = new GameWebSocketClient({
      gameId,
      playerKey: playerKey ?? undefined,
      onStateUpdate: (msg) => get().updateFromStateMessage(msg),
      onGameStarted: (msg) => get().handleGameStarted(msg),
      onGameOver: (msg) => get().handleGameOver(msg),
      onMoveRejected: (msg) => get().handleMoveRejected(msg),
      onError: (msg) => get().setError(msg.message),
      onConnectionChange: (state) => get().setConnectionState(state),
      onReconnected: () => get().resyncState(),
    });

    set({ wsClient: client });
    client.connect();
  },

  disconnect: () => {
    const { wsClient } = get();
    if (wsClient) {
      wsClient.disconnect();
    }
    set({ wsClient: null, connectionState: 'disconnected' });
  },

  resyncState: async () => {
    const { gameId } = get();
    if (!gameId) {
      return;
    }

    try {
      const gameState = await api.getGameState(gameId);
      set({
        status: gameState.status,
        currentTick: gameState.current_tick,
        winner: gameState.winner,
        pieces: gameState.board.pieces.map(convertApiPiece),
        activeMoves: gameState.active_moves.map(convertApiActiveMove),
        cooldowns: gameState.cooldowns.map(convertApiCooldown),
        // Clear any stale UI state
        selectedPieceId: null,
        legalMoves: [],
      });
    } catch (error) {
      console.error('Failed to resync state:', error);
    }
  },

  markReady: () => {
    const { wsClient } = get();
    if (wsClient) {
      wsClient.sendReady();
    }
  },

  selectPiece: (pieceId) => {
    const { pieces, playerNumber, status } = get();

    if (!pieceId) {
      set({ selectedPieceId: null, legalMoves: [] });
      return;
    }

    // Can't select pieces if not playing or if spectator
    if (status !== 'playing' || playerNumber === 0) {
      return;
    }

    // Verify the piece belongs to the player
    const piece = pieces.find((p) => p.id === pieceId);
    if (!piece || piece.player !== playerNumber) {
      return;
    }

    // Can't select captured, moving, or on-cooldown pieces
    if (piece.captured || piece.moving || piece.onCooldown) {
      return;
    }

    set({ selectedPieceId: pieceId });

    // Fetch legal moves for this piece
    get().fetchLegalMoves();
  },

  makeMove: (toRow, toCol) => {
    const { wsClient, selectedPieceId } = get();

    if (!wsClient || !selectedPieceId) {
      return;
    }

    wsClient.sendMove(selectedPieceId, toRow, toCol);

    // Don't clear selection here - wait for move confirmation or rejection
    // Selection will be cleared in updateFromStateMessage when piece starts moving
  },

  fetchLegalMoves: async () => {
    const { gameId, playerKey } = get();

    if (!gameId || !playerKey) {
      return;
    }

    try {
      const response = await api.getLegalMoves(gameId, playerKey);
      const moves: LegalMove[] = response.moves.map((m) => ({
        pieceId: m.piece_id,
        targets: m.targets,
      }));
      set({ legalMoves: moves });
    } catch (error) {
      console.error('Failed to fetch legal moves:', error);
    }
  },

  updateFromStateMessage: (msg) => {
    const { pieces: existingPieces, selectedPieceId } = get();

    // Merge piece updates
    const updatedPieces = mergePieceUpdates(existingPieces, msg.pieces);

    // Convert active moves and cooldowns
    const activeMoves: ActiveMove[] = msg.active_moves.map((m) => ({
      pieceId: m.piece_id,
      path: m.path,
      startTick: m.start_tick,
      progress: m.progress ?? 0,
    }));

    const cooldowns: Cooldown[] = msg.cooldowns.map((c) => ({
      pieceId: c.piece_id,
      remainingTicks: c.remaining_ticks,
    }));

    // Clear selection if the selected piece started moving
    let newSelectedPieceId = selectedPieceId;
    let newLegalMoves = get().legalMoves;
    if (selectedPieceId) {
      const pieceIsMoving = activeMoves.some((m) => m.pieceId === selectedPieceId);
      if (pieceIsMoving) {
        newSelectedPieceId = null;
        newLegalMoves = [];
      }
    }

    set({
      currentTick: msg.tick,
      pieces: updatedPieces,
      activeMoves,
      cooldowns,
      selectedPieceId: newSelectedPieceId,
      legalMoves: newLegalMoves,
    });
  },

  handleGameStarted: (msg) => {
    set({
      status: 'playing',
      currentTick: msg.tick,
    });
  },

  handleGameOver: (msg) => {
    set({
      status: 'finished',
      winner: msg.winner,
      winReason: msg.reason,
    });
  },

  handleMoveRejected: (msg) => {
    console.warn('Move rejected:', msg.piece_id, msg.reason);
    set({ lastError: `Move rejected: ${msg.reason}` });
  },

  setConnectionState: (state) => {
    set({ connectionState: state });
  },

  setError: (error) => {
    set({ lastError: error });
  },

  reset: () => {
    const { wsClient } = get();
    if (wsClient) {
      wsClient.disconnect();
    }
    set({ ...initialState });
  },
}));

// ============================================
// Selectors (for performance optimization)
// ============================================

export const selectPiece = (pieceId: string) => (state: GameStore) =>
  state.pieces.find((p) => p.id === pieceId);

export const selectSelectedPieceMoves = (state: GameStore) => {
  if (!state.selectedPieceId) return [];
  const move = state.legalMoves.find((m) => m.pieceId === state.selectedPieceId);
  return move?.targets ?? [];
};

export const selectIsMyPiece = (pieceId: string) => (state: GameStore) => {
  const piece = state.pieces.find((p) => p.id === pieceId);
  return piece?.player === state.playerNumber;
};

export const selectCanSelectPiece = (pieceId: string) => (state: GameStore) => {
  const piece = state.pieces.find((p) => p.id === pieceId);
  if (!piece) return false;
  return (
    piece.player === state.playerNumber &&
    !piece.captured &&
    !piece.moving &&
    !piece.onCooldown &&
    state.status === 'playing'
  );
};
