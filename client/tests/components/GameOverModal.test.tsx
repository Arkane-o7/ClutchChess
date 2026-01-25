import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { GameOverModal } from '../../src/components/game/GameOverModal';
import { useGameStore } from '../../src/stores/game';
import { useLobbyStore } from '../../src/stores/lobby';

// Helper component to track navigation
function LocationDisplay() {
  const location = useLocation();
  return <div data-testid="location">{location.pathname}</div>;
}

// Helper to render with router
const renderWithRouter = (ui: React.ReactElement) => {
  return render(
    <MemoryRouter initialEntries={['/game/test123']}>
      <Routes>
        <Route path="/game/:gameId" element={ui} />
        <Route path="/lobby/:code" element={<LocationDisplay />} />
        <Route path="/replay/:gameId" element={<LocationDisplay />} />
        <Route path="/" element={<LocationDisplay />} />
      </Routes>
    </MemoryRouter>
  );
};

describe('GameOverModal', () => {
  beforeEach(() => {
    // Reset stores between tests
    useGameStore.getState().reset();
    useLobbyStore.getState().reset();

    // Clear session storage
    sessionStorage.clear();
  });

  describe('Visibility', () => {
    it('does not render when game is not finished', () => {
      useGameStore.setState({ status: 'playing' });

      renderWithRouter(<GameOverModal />);
      expect(screen.queryByText(/Win|Lose|Draw|Game Over/)).not.toBeInTheDocument();
    });

    it('renders when game is finished', () => {
      useGameStore.setState({ status: 'finished', winner: 1, playerNumber: 1 });

      renderWithRouter(<GameOverModal />);
      expect(screen.getByText('You Win!')).toBeInTheDocument();
    });
  });

  describe('Result Display', () => {
    it('shows You Win when player wins', () => {
      useGameStore.setState({
        status: 'finished',
        winner: 1,
        playerNumber: 1,
      });

      renderWithRouter(<GameOverModal />);
      expect(screen.getByText('You Win!')).toBeInTheDocument();
    });

    it('shows You Lose when player loses', () => {
      useGameStore.setState({
        status: 'finished',
        winner: 2,
        playerNumber: 1,
      });

      renderWithRouter(<GameOverModal />);
      expect(screen.getByText('You Lose')).toBeInTheDocument();
    });

    it('shows Draw when draw', () => {
      useGameStore.setState({
        status: 'finished',
        winner: 0,
        playerNumber: 1,
      });

      renderWithRouter(<GameOverModal />);
      expect(screen.getByText('Draw!')).toBeInTheDocument();
    });

    it('shows win reason when provided', () => {
      useGameStore.setState({
        status: 'finished',
        winner: 1,
        playerNumber: 1,
        winReason: 'king_captured',
      });

      renderWithRouter(<GameOverModal />);
      expect(screen.getByText('King was captured')).toBeInTheDocument();
    });
  });

  describe('Return to Lobby Button', () => {
    it('shows Return to Lobby when lobbyCode is set in store', () => {
      useGameStore.setState({
        status: 'finished',
        winner: 1,
        playerNumber: 1,
        gameId: 'game123',
      });
      useLobbyStore.setState({ code: 'LOBBY1' });

      renderWithRouter(<GameOverModal />);
      expect(screen.getByRole('button', { name: 'Return to Lobby' })).toBeInTheDocument();
    });

    it('shows Return to Lobby when lobbyCode is in sessionStorage', () => {
      useGameStore.setState({
        status: 'finished',
        winner: 1,
        playerNumber: 1,
        gameId: 'game123',
      });
      sessionStorage.setItem('lobbyCode_game123', 'LOBBY2');

      renderWithRouter(<GameOverModal />);
      expect(screen.getByRole('button', { name: 'Return to Lobby' })).toBeInTheDocument();
    });

    it('does not show Return to Lobby when no lobby code', () => {
      useGameStore.setState({
        status: 'finished',
        winner: 1,
        playerNumber: 1,
        gameId: 'game123',
      });
      // No lobby code in store or session storage

      renderWithRouter(<GameOverModal />);
      expect(screen.queryByRole('button', { name: 'Return to Lobby' })).not.toBeInTheDocument();
    });

    it('calls returnToLobby and navigates when clicked', () => {
      const returnToLobby = vi.fn();
      const clearPendingGame = vi.fn();
      const reset = vi.fn();

      useGameStore.setState({
        status: 'finished',
        winner: 1,
        playerNumber: 1,
        gameId: 'game123',
        reset,
      });
      useLobbyStore.setState({
        code: 'LOBBY1',
        returnToLobby,
        clearPendingGame,
      });

      renderWithRouter(<GameOverModal />);
      fireEvent.click(screen.getByRole('button', { name: 'Return to Lobby' }));

      expect(returnToLobby).toHaveBeenCalled();
      expect(clearPendingGame).toHaveBeenCalled();
      expect(reset).toHaveBeenCalled();
    });
  });

  describe('View Replay Button', () => {
    it('shows View Replay when gameId is set', () => {
      useGameStore.setState({
        status: 'finished',
        winner: 1,
        playerNumber: 1,
        gameId: 'game123',
      });

      renderWithRouter(<GameOverModal />);
      expect(screen.getByRole('button', { name: 'View Replay' })).toBeInTheDocument();
    });

    it('does not show View Replay when gameId is not set', () => {
      useGameStore.setState({
        status: 'finished',
        winner: 1,
        playerNumber: 1,
        gameId: null,
      });

      renderWithRouter(<GameOverModal />);
      expect(screen.queryByRole('button', { name: 'View Replay' })).not.toBeInTheDocument();
    });
  });

  describe('Back to Home Button', () => {
    it('always shows Back to Home button', () => {
      useGameStore.setState({
        status: 'finished',
        winner: 1,
        playerNumber: 1,
      });

      renderWithRouter(<GameOverModal />);
      expect(screen.getByRole('button', { name: 'Back to Home' })).toBeInTheDocument();
    });

    it('calls reset when Back to Home is clicked', () => {
      const reset = vi.fn();
      const clearPendingGame = vi.fn();

      useGameStore.setState({
        status: 'finished',
        winner: 1,
        playerNumber: 1,
        reset,
      });
      useLobbyStore.setState({ clearPendingGame });

      renderWithRouter(<GameOverModal />);
      fireEvent.click(screen.getByRole('button', { name: 'Back to Home' }));

      expect(reset).toHaveBeenCalled();
      expect(clearPendingGame).toHaveBeenCalled();
    });
  });

  describe('Spectator Mode', () => {
    it('shows neutral message for spectator', () => {
      useGameStore.setState({
        status: 'finished',
        winner: 1,
        playerNumber: 0, // Spectator
      });

      renderWithRouter(<GameOverModal />);
      expect(screen.getByText('White Wins!')).toBeInTheDocument();
    });
  });
});
