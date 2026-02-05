"""Fire-and-forget helpers for active game registration."""

import asyncio
import logging

from kfchess.db.repositories.active_games import ActiveGameRepository
from kfchess.db.session import async_session_factory
from kfchess.settings import get_settings

logger = logging.getLogger(__name__)

# Store references to background tasks to prevent garbage collection.
# See: https://docs.python.org/3/library/asyncio-task.html#creating-tasks
_background_tasks: set[asyncio.Task] = set()


async def _register_game(
    game_id: str,
    game_type: str,
    speed: str,
    player_count: int,
    board_type: str,
    players: list[dict],
    lobby_code: str | None = None,
    campaign_level_id: int | None = None,
) -> None:
    """Register a game in the database (runs in background)."""
    try:
        server_id = get_settings().effective_server_id
        async with async_session_factory() as session:
            repo = ActiveGameRepository(session)
            await repo.register(
                game_id=game_id,
                game_type=game_type,
                speed=speed,
                player_count=player_count,
                board_type=board_type,
                players=players,
                server_id=server_id,
                lobby_code=lobby_code,
                campaign_level_id=campaign_level_id,
            )
            await session.commit()
    except Exception:
        logger.exception(f"Failed to register active game {game_id}")


async def _deregister_game(game_id: str) -> None:
    """Deregister a game from the database (runs in background)."""
    try:
        async with async_session_factory() as session:
            repo = ActiveGameRepository(session)
            await repo.deregister(game_id)
            await session.commit()
    except Exception:
        logger.exception(f"Failed to deregister active game {game_id}")


def register_game_fire_and_forget(
    game_id: str,
    game_type: str,
    speed: str,
    player_count: int,
    board_type: str,
    players: list[dict],
    lobby_code: str | None = None,
    campaign_level_id: int | None = None,
) -> None:
    """Schedule game registration as a fire-and-forget task."""
    task = asyncio.create_task(
        _register_game(
            game_id=game_id,
            game_type=game_type,
            speed=speed,
            player_count=player_count,
            board_type=board_type,
            players=players,
            lobby_code=lobby_code,
            campaign_level_id=campaign_level_id,
        )
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


def deregister_game_fire_and_forget(game_id: str) -> None:
    """Schedule game deregistration as a fire-and-forget task."""
    task = asyncio.create_task(_deregister_game(game_id))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
