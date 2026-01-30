/**
 * Tests for the ResignButton component
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ResignButton } from '../../src/components/game/ResignButton';
import { useGameStore } from '../../src/stores/game';

describe('ResignButton', () => {
  beforeEach(() => {
    useGameStore.getState().reset();
  });

  describe('Visibility', () => {
    it('does not render for spectators', () => {
      useGameStore.setState({ playerNumber: 0, status: 'playing' });
      const { container } = render(<ResignButton />);
      expect(container.innerHTML).toBe('');
    });

    it('does not render when game is not playing', () => {
      useGameStore.setState({ playerNumber: 1, status: 'waiting' });
      const { container } = render(<ResignButton />);
      expect(container.innerHTML).toBe('');
    });

    it('does not render when game is finished', () => {
      useGameStore.setState({ playerNumber: 1, status: 'finished' });
      const { container } = render(<ResignButton />);
      expect(container.innerHTML).toBe('');
    });

    it('renders for active player during gameplay', () => {
      useGameStore.setState({
        playerNumber: 1,
        status: 'playing',
        pieces: [{ id: 'K:1:7:4', type: 'K', player: 1, row: 7, col: 4, captured: false, moving: false, onCooldown: false, moved: false }],
      });
      render(<ResignButton />);
      expect(screen.getByRole('button', { name: 'Resign' })).toBeInTheDocument();
    });

    it('does not render for eliminated player in 4-player mode', () => {
      useGameStore.setState({
        playerNumber: 1,
        status: 'playing',
        pieces: [{ id: 'K:1:7:4', type: 'K', player: 1, row: 7, col: 4, captured: true, moving: false, onCooldown: false, moved: false }],
      });
      const { container } = render(<ResignButton />);
      expect(container.innerHTML).toBe('');
    });
  });

  describe('Confirmation Modal', () => {
    beforeEach(() => {
      useGameStore.setState({
        playerNumber: 1,
        status: 'playing',
        pieces: [{ id: 'K:1:7:4', type: 'K', player: 1, row: 7, col: 4, captured: false, moving: false, onCooldown: false, moved: false }],
      });
    });

    it('shows confirmation modal when resign button is clicked', () => {
      render(<ResignButton />);
      fireEvent.click(screen.getByRole('button', { name: 'Resign' }));
      expect(screen.getByText('Are you sure you want to resign?')).toBeInTheDocument();
    });

    it('hides confirmation modal when cancel is clicked', () => {
      render(<ResignButton />);
      fireEvent.click(screen.getByRole('button', { name: 'Resign' }));
      fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
      expect(screen.queryByText('Are you sure you want to resign?')).not.toBeInTheDocument();
    });

    it('calls resign on confirm', () => {
      const resignSpy = vi.fn();
      useGameStore.setState({ resign: resignSpy });

      render(<ResignButton />);
      fireEvent.click(screen.getByRole('button', { name: 'Resign' }));

      // Click the confirm button (second "Resign" button in the modal)
      const buttons = screen.getAllByRole('button', { name: 'Resign' });
      fireEvent.click(buttons[1]);

      expect(resignSpy).toHaveBeenCalledOnce();
    });
  });
});
