/**
 * Rating and Belt Utilities
 *
 * Functions for working with ELO ratings and belt rankings.
 * Mirrors the server-side logic in server/src/kfchess/game/elo.py
 */

import { staticUrl } from '../config';

export const DEFAULT_RATING = 1200;

// Belt thresholds - ordered highest to lowest
const BELT_THRESHOLDS: [number, string][] = [
  [2300, 'black'],
  [2100, 'red'],
  [1900, 'brown'],
  [1700, 'blue'],
  [1500, 'orange'],
  [1300, 'purple'],
  [1100, 'green'],
  [900, 'yellow'],
  [0, 'white'],
];

/**
 * Get belt name for a given rating.
 * Returns 'none' for null/undefined ratings.
 */
export function getBelt(rating: number | null | undefined): string {
  if (rating === null || rating === undefined) {
    return 'none';
  }
  for (const [threshold, belt] of BELT_THRESHOLDS) {
    if (rating >= threshold) {
      return belt;
    }
  }
  return 'white';
}

/**
 * Get the display name for a belt.
 */
export function getBeltDisplayName(belt: string): string {
  return belt.charAt(0).toUpperCase() + belt.slice(1);
}

/**
 * Get the URL for a belt icon.
 */
export function getBeltIconUrl(belt: string): string {
  return staticUrl(`belt-${belt}.png`);
}

/**
 * Get the URL for a belt icon based on rating.
 */
export function getBeltIconUrlForRating(rating: number | null | undefined): string {
  return getBeltIconUrl(getBelt(rating));
}

/**
 * Rating mode types
 */
export type RatingMode = '2p_standard' | '2p_lightning' | '4p_standard' | '4p_lightning';

/**
 * Format a rating mode key into a display name.
 * e.g., "2p_standard" -> "2-Player Standard"
 */
export function formatModeName(mode: string): string {
  const parts = mode.split('_');
  if (parts.length !== 2) return mode;

  const [players, speed] = parts;
  const playerText = players === '2p' ? '2-Player' : '4-Player';
  const speedText = speed.charAt(0).toUpperCase() + speed.slice(1);

  return `${playerText} ${speedText}`;
}

/**
 * Format a rating mode key into a short display name.
 * e.g., "2p_standard" -> "2P Std"
 */
export function formatModeNameShort(mode: string): string {
  const parts = mode.split('_');
  if (parts.length !== 2) return mode;

  const [players, speed] = parts;
  const playerText = players === '2p' ? '2P' : '4P';
  const speedText = speed === 'standard' ? 'Std' : 'Ltng';

  return `${playerText} ${speedText}`;
}

/**
 * All rating modes in display order
 */
export const RATING_MODES: RatingMode[] = [
  '2p_standard',
  '2p_lightning',
  '4p_standard',
  '4p_lightning',
];

/**
 * Rating stats for a single mode (matches server format)
 */
export interface RatingStats {
  rating: number;
  games: number;
  wins: number;
}

/**
 * Rating change data from server
 */
export interface RatingChangeData {
  oldRating: number;
  newRating: number;
  oldBelt: string;
  newBelt: string;
  beltChanged: boolean;
}

/**
 * Format a rating change as a string with sign.
 * e.g., +15 or -8
 */
export function formatRatingChange(oldRating: number, newRating: number): string {
  const diff = newRating - oldRating;
  if (diff > 0) {
    return `+${diff}`;
  }
  return String(diff);
}

/**
 * Get CSS class for rating change (positive/negative)
 */
export function getRatingChangeClass(oldRating: number, newRating: number): string {
  const diff = newRating - oldRating;
  if (diff > 0) return 'rating-change-positive';
  if (diff < 0) return 'rating-change-negative';
  return 'rating-change-neutral';
}
