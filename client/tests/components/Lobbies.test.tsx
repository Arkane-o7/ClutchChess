import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { Lobbies } from '../../src/pages/Lobbies';
import { useLobbyStore } from '../../src/stores/lobby';
import type { LobbyListItem, LobbySettings } from '../../src/api/types';

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

const createMockLobbyListItem = (overrides?: Partial<LobbyListItem>): LobbyListItem => ({
  id: 1,
  code: 'ABC123',
  hostUsername: 'TestHost',
  settings: createMockSettings(),
  playerCount: 2,
  currentPlayers: 1,
  status: 'waiting',
  ...overrides,
});

// Helper to render with router
const renderWithRouter = (ui: React.ReactElement) => {
  return render(
    <MemoryRouter initialEntries={['/lobbies']}>
      <Routes>
        <Route path="/lobbies" element={ui} />
        <Route path="/lobby/:code" element={<div>Lobby Page</div>} />
      </Routes>
    </MemoryRouter>
  );
};

// ============================================
// Tests
// ============================================

describe('Lobbies Page', () => {
  beforeEach(() => {
    // Reset store between tests
    useLobbyStore.getState().reset();
    // Mock fetchPublicLobbies to prevent actual API calls
    useLobbyStore.setState({
      fetchPublicLobbies: vi.fn(),
    });
  });

  describe('Header', () => {
    it('renders page title', () => {
      renderWithRouter(<Lobbies />);
      expect(screen.getByText('Browse Lobbies')).toBeInTheDocument();
    });

    it('renders Create Lobby button', () => {
      renderWithRouter(<Lobbies />);
      expect(screen.getByRole('button', { name: 'Create Lobby' })).toBeInTheDocument();
    });
  });

  describe('Filters', () => {
    it('renders filter dropdowns', () => {
      renderWithRouter(<Lobbies />);
      const selects = screen.getAllByRole('combobox');
      expect(selects.length).toBe(3); // Speed, Player Count, Rated
    });

    it('renders speed filter options', () => {
      renderWithRouter(<Lobbies />);
      expect(screen.getByText('All Speeds')).toBeInTheDocument();
      expect(screen.getByText('Standard')).toBeInTheDocument();
      expect(screen.getByText('Lightning')).toBeInTheDocument();
    });

    it('renders player count filter options', () => {
      renderWithRouter(<Lobbies />);
      expect(screen.getByText('All Player Counts')).toBeInTheDocument();
      expect(screen.getByText('2 Players')).toBeInTheDocument();
      expect(screen.getByText('4 Players')).toBeInTheDocument();
    });

    it('renders rated filter options', () => {
      renderWithRouter(<Lobbies />);
      expect(screen.getByText('All Types')).toBeInTheDocument();
      expect(screen.getByText('Rated')).toBeInTheDocument();
      expect(screen.getByText('Unrated')).toBeInTheDocument();
    });
  });

  describe('Loading State', () => {
    it('shows loading message when loading with no lobbies', () => {
      useLobbyStore.setState({
        isLoadingLobbies: true,
        publicLobbies: [],
      });

      renderWithRouter(<Lobbies />);
      expect(screen.getByText('Loading lobbies...')).toBeInTheDocument();
    });
  });

  describe('Empty State', () => {
    it('shows empty message when no lobbies available', () => {
      useLobbyStore.setState({
        isLoadingLobbies: false,
        publicLobbies: [],
      });

      renderWithRouter(<Lobbies />);
      expect(screen.getByText('No public lobbies available.')).toBeInTheDocument();
      expect(screen.getByText('Create one or join by code!')).toBeInTheDocument();
    });
  });

  describe('Lobby List', () => {
    it('renders lobby cards when lobbies exist', () => {
      useLobbyStore.setState({
        isLoadingLobbies: false,
        publicLobbies: [
          createMockLobbyListItem({ hostUsername: 'Player1' }),
          createMockLobbyListItem({ id: 2, code: 'DEF456', hostUsername: 'Player2' }),
        ],
      });

      renderWithRouter(<Lobbies />);
      expect(screen.getByText("Player1's Lobby")).toBeInTheDocument();
      expect(screen.getByText("Player2's Lobby")).toBeInTheDocument();
    });

    it('shows lobby settings in card', () => {
      useLobbyStore.setState({
        isLoadingLobbies: false,
        publicLobbies: [
          createMockLobbyListItem({
            settings: createMockSettings({ speed: 'lightning', playerCount: 4 }),
          }),
        ],
      });

      renderWithRouter(<Lobbies />);
      expect(screen.getByText('lightning')).toBeInTheDocument();
      expect(screen.getByText('4 players')).toBeInTheDocument();
    });

    it('shows player count on lobby card', () => {
      useLobbyStore.setState({
        isLoadingLobbies: false,
        publicLobbies: [
          createMockLobbyListItem({ currentPlayers: 1, playerCount: 2 }),
        ],
      });

      renderWithRouter(<Lobbies />);
      expect(screen.getByText('1/2')).toBeInTheDocument();
    });

    it('shows Join button on lobby card', () => {
      useLobbyStore.setState({
        isLoadingLobbies: false,
        publicLobbies: [createMockLobbyListItem()],
      });

      renderWithRouter(<Lobbies />);
      // There are two Join buttons - one on the lobby card, one in the join-by-code section
      const joinButtons = screen.getAllByRole('button', { name: 'Join' });
      expect(joinButtons.length).toBeGreaterThanOrEqual(1);
    });

    it('shows Full and disables button when lobby is full', () => {
      useLobbyStore.setState({
        isLoadingLobbies: false,
        publicLobbies: [
          createMockLobbyListItem({ currentPlayers: 2, playerCount: 2 }),
        ],
      });

      renderWithRouter(<Lobbies />);
      const fullButton = screen.getByRole('button', { name: 'Full' });
      expect(fullButton).toBeInTheDocument();
      expect(fullButton).toBeDisabled();
    });

    it('shows Ranked badge for ranked lobbies', () => {
      useLobbyStore.setState({
        isLoadingLobbies: false,
        publicLobbies: [
          createMockLobbyListItem({
            settings: createMockSettings({ isRanked: true }),
          }),
        ],
      });

      renderWithRouter(<Lobbies />);
      expect(screen.getByText('Ranked')).toBeInTheDocument();
    });
  });

  describe('Join by Code', () => {
    it('renders join by code section', () => {
      renderWithRouter(<Lobbies />);
      expect(screen.getByText('Join by Code')).toBeInTheDocument();
    });

    it('renders code input', () => {
      renderWithRouter(<Lobbies />);
      expect(screen.getByPlaceholderText('Enter lobby code')).toBeInTheDocument();
    });

    it('renders join button (disabled when empty)', () => {
      renderWithRouter(<Lobbies />);
      const joinButtons = screen.getAllByRole('button', { name: 'Join' });
      // The join by code button is different from lobby card join buttons
      const codeJoinButton = joinButtons.find((btn) => btn.closest('.join-code-form'));
      expect(codeJoinButton).toBeDisabled();
    });

    it('enables join button when code is entered', () => {
      renderWithRouter(<Lobbies />);
      const input = screen.getByPlaceholderText('Enter lobby code');
      fireEvent.change(input, { target: { value: 'ABC123' } });

      const joinButtons = screen.getAllByRole('button', { name: 'Join' });
      const codeJoinButton = joinButtons.find((btn) => btn.closest('.join-code-form'));
      expect(codeJoinButton).not.toBeDisabled();
    });

    it('converts input to uppercase', () => {
      renderWithRouter(<Lobbies />);
      const input = screen.getByPlaceholderText('Enter lobby code') as HTMLInputElement;
      fireEvent.change(input, { target: { value: 'abc123' } });

      expect(input.value).toBe('ABC123');
    });
  });

  describe('Join Modal', () => {
    it('shows join modal when clicking Join on a lobby', () => {
      useLobbyStore.setState({
        isLoadingLobbies: false,
        publicLobbies: [createMockLobbyListItem({ hostUsername: 'TestHost' })],
      });

      renderWithRouter(<Lobbies />);
      // Click the Join button on the lobby card (first one, not the join-by-code one)
      const joinButtons = screen.getAllByRole('button', { name: 'Join' });
      fireEvent.click(joinButtons[0]);

      // Modal heading
      expect(screen.getByRole('heading', { name: 'Join Lobby' })).toBeInTheDocument();
      // Modal subtitle contains host info
      expect(screen.getByText(/standard, 2 players/)).toBeInTheDocument();
    });

    it('shows username input for guests in join modal', () => {
      useLobbyStore.setState({
        isLoadingLobbies: false,
        publicLobbies: [createMockLobbyListItem()],
      });

      renderWithRouter(<Lobbies />);
      const joinButtons = screen.getAllByRole('button', { name: 'Join' });
      fireEvent.click(joinButtons[0]);

      expect(screen.getByLabelText(/Display Name/i)).toBeInTheDocument();
    });

    it('closes modal when Cancel is clicked', () => {
      useLobbyStore.setState({
        isLoadingLobbies: false,
        publicLobbies: [createMockLobbyListItem()],
      });

      renderWithRouter(<Lobbies />);
      const joinButtons = screen.getAllByRole('button', { name: 'Join' });
      fireEvent.click(joinButtons[0]);
      fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));

      // Modal heading should be gone
      expect(screen.queryByRole('heading', { name: 'Join Lobby' })).not.toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    it('shows error banner when create fails', async () => {
      const mockCreateLobby = vi.fn().mockRejectedValue(new Error('Failed to create'));
      useLobbyStore.setState({
        isLoadingLobbies: false,
        publicLobbies: [],
        createLobby: mockCreateLobby,
      });

      renderWithRouter(<Lobbies />);
      fireEvent.click(screen.getByRole('button', { name: 'Create Lobby' }));

      await waitFor(() => {
        expect(screen.getByText('Failed to create')).toBeInTheDocument();
      });
    });

    it('dismisses error when clicking dismiss', async () => {
      const mockCreateLobby = vi.fn().mockRejectedValue(new Error('Failed to create'));
      useLobbyStore.setState({
        isLoadingLobbies: false,
        publicLobbies: [],
        createLobby: mockCreateLobby,
      });

      renderWithRouter(<Lobbies />);
      fireEvent.click(screen.getByRole('button', { name: 'Create Lobby' }));

      await waitFor(() => {
        expect(screen.getByText('Failed to create')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole('button', { name: 'Dismiss' }));
      expect(screen.queryByText('Failed to create')).not.toBeInTheDocument();
    });
  });

  describe('Create Lobby', () => {
    it('shows Creating... when creating lobby', async () => {
      const mockCreateLobby = vi.fn().mockImplementation(() => new Promise(() => {})); // Never resolves
      useLobbyStore.setState({
        isLoadingLobbies: false,
        publicLobbies: [],
        createLobby: mockCreateLobby,
      });

      renderWithRouter(<Lobbies />);
      fireEvent.click(screen.getByRole('button', { name: 'Create Lobby' }));

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Creating...' })).toBeInTheDocument();
      });
    });

    it('disables create button while creating', async () => {
      const mockCreateLobby = vi.fn().mockImplementation(() => new Promise(() => {}));
      useLobbyStore.setState({
        isLoadingLobbies: false,
        publicLobbies: [],
        createLobby: mockCreateLobby,
      });

      renderWithRouter(<Lobbies />);
      fireEvent.click(screen.getByRole('button', { name: 'Create Lobby' }));

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Creating...' })).toBeDisabled();
      });
    });
  });
});
