"""Leaderboard API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from clutchchess.db.session import get_db_session
from clutchchess.game.elo import get_belt

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])

VALID_MODES = {"2p_standard", "2p_lightning", "4p_standard", "4p_lightning"}


class LeaderboardEntry(BaseModel):
    """Single entry in the leaderboard."""

    rank: int
    user_id: int
    username: str
    picture_url: str | None
    rating: int
    belt: str
    games_played: int
    wins: int


class LeaderboardResponse(BaseModel):
    """Response for leaderboard queries."""

    mode: str
    entries: list[LeaderboardEntry]


@router.get("", response_model=LeaderboardResponse)
async def get_leaderboard(
    mode: str = Query(..., pattern="^(2p|4p)_(standard|lightning)$"),
    db: Annotated[AsyncSession, Depends(get_db_session)] = ...,
) -> JSONResponse:
    """Get top 100 leaderboard for a specific rating mode.

    Results are cached for 60 seconds to reduce database load.
    """
    query = text("""
        SELECT
            id,
            username,
            picture_url,
            (ratings->:mode->>'rating')::int as rating,
            (ratings->:mode->>'games')::int as games_played,
            (ratings->:mode->>'wins')::int as wins
        FROM users
        WHERE ratings ? :mode
          AND (ratings->:mode->>'games')::int > 0
        ORDER BY (ratings->:mode->>'rating')::int DESC
        LIMIT 100
    """)

    result = await db.execute(query, {"mode": mode})
    rows = result.fetchall()

    entries = [
        LeaderboardEntry(
            rank=i + 1,
            user_id=row.id,
            username=row.username,
            picture_url=row.picture_url,
            rating=row.rating,
            belt=get_belt(row.rating),
            games_played=row.games_played,
            wins=row.wins,
        )
        for i, row in enumerate(rows)
    ]

    response = JSONResponse(
        content=LeaderboardResponse(
            mode=mode,
            entries=entries,
        ).model_dump()
    )
    response.headers["Cache-Control"] = "public, max-age=60"
    return response
