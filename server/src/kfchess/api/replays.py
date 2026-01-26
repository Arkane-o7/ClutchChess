"""Replays API endpoints."""

from datetime import datetime

from fastapi import APIRouter, Query
from pydantic import BaseModel

from kfchess.db.repositories.replays import ReplayRepository
from kfchess.db.session import async_session_factory
from kfchess.utils.display_name import resolve_player_names

router = APIRouter(prefix="/replays", tags=["replays"])


class ReplaySummary(BaseModel):
    """Summary of a replay for listing."""

    game_id: str
    speed: str
    board_type: str
    players: dict[str, str]
    total_ticks: int
    winner: int | None
    win_reason: str | None
    created_at: datetime | None


class ReplayListResponse(BaseModel):
    """Response for listing replays."""

    replays: list[ReplaySummary]
    total: int


@router.get("", response_model=ReplayListResponse)
async def list_replays(
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
) -> ReplayListResponse:
    """List recent replays.

    Args:
        limit: Maximum number of replays to return (1-50)
        offset: Number of replays to skip

    Returns:
        List of replay summaries with resolved player display names
    """
    async with async_session_factory() as session:
        repository = ReplayRepository(session)
        replays_with_ids = await repository.list_recent(limit=limit, offset=offset)
        total = await repository.count_public()

        # Resolve player display names for all replays
        summaries = []
        for game_id, replay in replays_with_ids:
            # Convert string keys back to int for resolve_player_names
            players_int_keys = {int(k): v for k, v in replay.players.items()}
            resolved_players = await resolve_player_names(session, players_int_keys)

            summaries.append(
                ReplaySummary(
                    game_id=game_id,
                    speed=replay.speed.value,
                    board_type=replay.board_type.value,
                    players={str(k): v for k, v in resolved_players.items()},
                    total_ticks=replay.total_ticks,
                    winner=replay.winner,
                    win_reason=replay.win_reason,
                    created_at=replay.created_at,
                )
            )

    return ReplayListResponse(replays=summaries, total=total)
