/**
 * Display Name Utilities
 *
 * Formats player names for display in the UI.
 */

import type { LobbyPlayer } from '../api/types';

/**
 * Format a player's display name.
 *
 * - AI players: "AI (type)" e.g., "AI (Novice)"
 * - Guest players (no userId): "Guest"
 * - Logged in players: their username
 */
export function formatDisplayName(player: LobbyPlayer): string {
  if (player.isAi && player.aiType) {
    // Format AI type: "bot:novice" -> "Novice"
    const aiName = player.aiType.replace('bot:', '');
    const capitalizedName = aiName.charAt(0).toUpperCase() + aiName.slice(1);
    return `AI (${capitalizedName})`;
  }

  if (player.userId === null) {
    return 'Guest';
  }

  return player.username;
}
