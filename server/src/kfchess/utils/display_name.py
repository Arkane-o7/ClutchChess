"""Display name utilities for player identity formatting.

This module provides functions to convert internal player IDs to user-friendly
display names. Player IDs have the format:
- u:{user_id} - Registered user (resolve username from database)
- guest:{uuid} - Anonymous guest player
- bot:{type} - AI player (e.g., bot:dummy)
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kfchess.db.models import User


def format_player_id(player_id: str, username_map: dict[int, str] | None = None) -> str:
    """Format a player ID into a display name.

    Args:
        player_id: Internal player ID (e.g., "u:123", "guest:abc", "bot:dummy")
        username_map: Optional map of user_id -> username for resolving user names

    Returns:
        Human-readable display name
    """
    if player_id.startswith("u:"):
        # Registered user - look up username
        user_id_str = player_id[2:]
        try:
            user_id = int(user_id_str)
            if username_map and user_id in username_map:
                return username_map[user_id]
        except ValueError:
            pass
        # Fallback if we can't resolve
        return f"User {user_id_str}"

    if player_id.startswith("guest:"):
        return "Guest"

    if player_id.startswith("bot:"):
        bot_type = player_id[4:]  # e.g., "dummy"
        # Capitalize first letter
        bot_name = bot_type.capitalize()
        return f"AI ({bot_name})"

    # Unknown format - return as-is
    return player_id


def extract_user_ids(player_ids: list[str]) -> list[int]:
    """Extract user IDs from a list of player IDs.

    Args:
        player_ids: List of player IDs to extract user IDs from

    Returns:
        List of user IDs (integers) for players that are registered users
    """
    user_ids = []
    for player_id in player_ids:
        if player_id.startswith("u:"):
            try:
                user_id = int(player_id[2:])
                user_ids.append(user_id)
            except ValueError:
                pass
    return user_ids


async def fetch_usernames(
    session: AsyncSession, user_ids: list[int]
) -> dict[int, str]:
    """Fetch usernames for a list of user IDs.

    Args:
        session: Database session
        user_ids: List of user IDs to look up

    Returns:
        Dict mapping user_id -> username
    """
    if not user_ids:
        return {}

    result = await session.execute(
        select(User.id, User.username).where(User.id.in_(user_ids))
    )
    return {row.id: row.username for row in result.all()}


async def resolve_player_names(
    session: AsyncSession, players: dict[int, str]
) -> dict[int, str]:
    """Resolve a dict of player IDs to display names.

    Args:
        session: Database session
        players: Dict mapping player number to player ID

    Returns:
        Dict mapping player number to display name
    """
    # Extract all user IDs that need lookup
    user_ids = extract_user_ids(list(players.values()))

    # Batch fetch usernames
    username_map = await fetch_usernames(session, user_ids)

    # Format all player IDs
    return {
        num: format_player_id(player_id, username_map)
        for num, player_id in players.items()
    }
