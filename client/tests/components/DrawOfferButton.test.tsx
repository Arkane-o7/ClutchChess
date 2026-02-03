/**
 * Tests for the DrawOfferButton component
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { DrawOfferButton } from '../../src/components/game/DrawOfferButton';
import { useGameStore } from '../../src/stores/game';

const activeKing = { id: 'K:1:7:4', type: 'K' as const, player: 1, row: 7, col: 4, captured: false, moving: false, onCooldown: false, moved: false };
const activeKing2 = { id: 'K:2:0:4', type: 'K' as const, player: 2, row: 0, col: 4, captured: false, moving: false, onCooldown: false, moved: false };

describe('DrawOfferButton', () => {
  beforeEach(() => {
    useGameStore.getState().reset();
  });

  describe('Visibility', () => {
    it('does not render for spectators', () => {
      useGameStore.setState({ playerNumber: 0, status: 'playing' });
      const { container } = render(<DrawOfferButton />);
      expect(container.innerHTML).toBe('');
    });

    it('does not render when game is not playing', () => {
      useGameStore.setState({ playerNumber: 1, status: 'waiting' });
      const { container } = render(<DrawOfferButton />);
      expect(container.innerHTML).toBe('');
    });

    it('renders for active player during gameplay', () => {
      useGameStore.setState({
        playerNumber: 1,
        status: 'playing',
        pieces: [activeKing],
        drawOffers: [],
        players: { '1': { name: 'P1', picture_url: null, user_id: 1, is_bot: false }, '2': { name: 'P2', picture_url: null, user_id: 2, is_bot: false } },
      });
      render(<DrawOfferButton />);
      expect(screen.getByRole('button', { name: 'Offer Draw' })).toBeInTheDocument();
    });

    it('does not render for eliminated player', () => {
      useGameStore.setState({
        playerNumber: 1,
        status: 'playing',
        pieces: [{ ...activeKing, captured: true }],
        drawOffers: [],
      });
      const { container } = render(<DrawOfferButton />);
      expect(container.innerHTML).toBe('');
    });

    it('shows disabled "Draw Offered" after player has already offered', () => {
      useGameStore.setState({
        playerNumber: 1,
        status: 'playing',
        pieces: [activeKing],
        drawOffers: [1],
        players: { '1': { name: 'P1', picture_url: null, user_id: 1, is_bot: false }, '2': { name: 'P2', picture_url: null, user_id: 2, is_bot: false } },
      });
      render(<DrawOfferButton />);
      const button = screen.getByRole('button', { name: 'Draw Offered' });
      expect(button).toBeDisabled();
    });
  });

  describe('Button text', () => {
    it('shows "Offer Draw" when no other humans have offered', () => {
      useGameStore.setState({
        playerNumber: 1,
        status: 'playing',
        pieces: [activeKing, activeKing2],
        drawOffers: [],
        players: { '1': { name: 'P1', picture_url: null, user_id: 1, is_bot: false }, '2': { name: 'P2', picture_url: null, user_id: 2, is_bot: false } },
      });
      render(<DrawOfferButton />);
      expect(screen.getByRole('button', { name: 'Offer Draw' })).toBeInTheDocument();
    });

    it('shows "Accept Draw" when all other humans have offered', () => {
      useGameStore.setState({
        playerNumber: 1,
        status: 'playing',
        pieces: [activeKing, activeKing2],
        drawOffers: [2],
        players: { '1': { name: 'P1', picture_url: null, user_id: 1, is_bot: false }, '2': { name: 'P2', picture_url: null, user_id: 2, is_bot: false } },
      });
      render(<DrawOfferButton />);
      expect(screen.getByRole('button', { name: 'Accept Draw' })).toBeInTheDocument();
    });

    it('does not render when all opponents are bots', () => {
      useGameStore.setState({
        playerNumber: 1,
        status: 'playing',
        pieces: [activeKing],
        drawOffers: [],
        players: { '1': { name: 'P1', picture_url: null, user_id: 1, is_bot: false }, '2': { name: 'Bot', picture_url: null, user_id: null, is_bot: true } },
      });
      const { container } = render(<DrawOfferButton />);
      expect(container.innerHTML).toBe('');
    });
  });

  describe('Action', () => {
    it('calls offerDraw when clicked', () => {
      const offerDrawSpy = vi.fn();
      useGameStore.setState({
        playerNumber: 1,
        status: 'playing',
        pieces: [activeKing, activeKing2],
        drawOffers: [],
        players: { '1': { name: 'P1', picture_url: null, user_id: 1, is_bot: false }, '2': { name: 'P2', picture_url: null, user_id: 2, is_bot: false } },
        offerDraw: offerDrawSpy,
      });

      render(<DrawOfferButton />);
      fireEvent.click(screen.getByRole('button'));
      expect(offerDrawSpy).toHaveBeenCalledOnce();
    });
  });
});
