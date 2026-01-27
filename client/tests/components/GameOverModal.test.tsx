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

  describe('Rating Change Display', () => {
    it('shows rating change when ratingChange is set', () => {
      useGameStore.setState({
        status: 'finished',
        winner: 1,
        playerNumber: 1,
        ratingChange: {
          oldRating: 1200,
          newRating: 1215,
          oldBelt: 'green',
          newBelt: 'green',
          beltChanged: false,
        },
      });

      renderWithRouter(<GameOverModal />);
      expect(screen.getByText('Rating')).toBeInTheDocument();
      expect(screen.getByText('+15')).toBeInTheDocument();
      expect(screen.getByText('1200')).toBeInTheDocument();
      expect(screen.getByText('1215')).toBeInTheDocument();
    });

    it('does not show rating change when ratingChange is null', () => {
      useGameStore.setState({
        status: 'finished',
        winner: 1,
        playerNumber: 1,
        ratingChange: null,
      });

      renderWithRouter(<GameOverModal />);
      expect(screen.queryByText('Rating')).not.toBeInTheDocument();
    });

    it('shows positive change with correct class', () => {
      useGameStore.setState({
        status: 'finished',
        winner: 1,
        playerNumber: 1,
        ratingChange: {
          oldRating: 1200,
          newRating: 1220,
          oldBelt: 'green',
          newBelt: 'green',
          beltChanged: false,
        },
      });

      renderWithRouter(<GameOverModal />);
      const changeElement = screen.getByText('+20');
      expect(changeElement).toHaveClass('rating-change-positive');
    });

    it('shows negative change with correct class', () => {
      useGameStore.setState({
        status: 'finished',
        winner: 2,
        playerNumber: 1,
        ratingChange: {
          oldRating: 1200,
          newRating: 1185,
          oldBelt: 'green',
          newBelt: 'green',
          beltChanged: false,
        },
      });

      renderWithRouter(<GameOverModal />);
      const changeElement = screen.getByText('-15');
      expect(changeElement).toHaveClass('rating-change-negative');
    });

    it('displays old and new rating values', () => {
      useGameStore.setState({
        status: 'finished',
        winner: 1,
        playerNumber: 1,
        ratingChange: {
          oldRating: 1350,
          newRating: 1380,
          oldBelt: 'purple',
          newBelt: 'purple',
          beltChanged: false,
        },
      });

      renderWithRouter(<GameOverModal />);
      expect(screen.getByText('1350')).toBeInTheDocument();
      expect(screen.getByText('1380')).toBeInTheDocument();
    });

    it('shows belt change UI when beltChanged is true', () => {
      useGameStore.setState({
        status: 'finished',
        winner: 1,
        playerNumber: 1,
        ratingChange: {
          oldRating: 1290,
          newRating: 1315,
          oldBelt: 'green',
          newBelt: 'purple',
          beltChanged: true,
        },
      });

      renderWithRouter(<GameOverModal />);
      expect(screen.getByText('New Belt!')).toBeInTheDocument();
      expect(screen.getByText('Purple')).toBeInTheDocument();
      // Check for belt icon
      const beltIcon = screen.getByAltText('purple');
      expect(beltIcon).toBeInTheDocument();
      expect(beltIcon).toHaveAttribute('src', expect.stringContaining('belt-purple.png'));
    });

    it('does not show belt change UI when beltChanged is false', () => {
      useGameStore.setState({
        status: 'finished',
        winner: 1,
        playerNumber: 1,
        ratingChange: {
          oldRating: 1200,
          newRating: 1215,
          oldBelt: 'green',
          newBelt: 'green',
          beltChanged: false,
        },
      });

      renderWithRouter(<GameOverModal />);
      expect(screen.queryByText('New Belt!')).not.toBeInTheDocument();
    });

    it('does not show rating change for spectators', () => {
      useGameStore.setState({
        status: 'finished',
        winner: 1,
        playerNumber: 0, // Spectator
        ratingChange: null, // Spectators won't have rating changes
      });

      renderWithRouter(<GameOverModal />);
      expect(screen.queryByText('Rating')).not.toBeInTheDocument();
    });

    it('handles draw with rating change', () => {
      useGameStore.setState({
        status: 'finished',
        winner: 0, // Draw
        playerNumber: 1,
        ratingChange: {
          oldRating: 1200,
          newRating: 1200, // No change in draw
          oldBelt: 'green',
          newBelt: 'green',
          beltChanged: false,
        },
      });

      renderWithRouter(<GameOverModal />);
      expect(screen.getByText('Draw!')).toBeInTheDocument();
      expect(screen.getByText('Rating')).toBeInTheDocument();
      expect(screen.getByText('0')).toBeInTheDocument();
    });
  });
});
