"""User API routes with DEV_MODE bypass support.

These routes replace FastAPI-Users' built-in /users routes to support
DEV_MODE authentication bypass for local development.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from kfchess.api.replays import ReplayListResponse, ReplaySummary
from kfchess.auth.dependencies import (
    get_required_user_with_dev_bypass,
    get_user_manager_dep,
)
from kfchess.auth.schemas import UserRead, UserUpdate
from kfchess.auth.users import UserManager
from kfchess.db.models import User
from kfchess.db.repositories.users import UserRepository
from kfchess.db.session import get_db_session
from kfchess.utils.display_name import resolve_player_names

router = APIRouter(prefix="/users", tags=["users"])


class PublicUserRead(BaseModel):
    """Public user profile data (excludes email and other sensitive fields)."""

    id: int
    username: str
    picture_url: str | None
    ratings: dict
    created_at: datetime
    last_online: datetime


@router.get("/me", response_model=UserRead)
async def get_current_user_info(
    user: Annotated[User, Depends(get_required_user_with_dev_bypass)],
) -> User:
    """Get the current user's information.

    This endpoint supports DEV_MODE bypass - when DEV_MODE=true and
    DEV_USER_ID is set, returns the dev user without authentication.

    Returns:
        Current user's data
    """
    return user


class UserUpdateRequest(BaseModel):
    """Request model for user updates."""

    password: str | None = None
    username: str | None = None
    picture_url: str | None = None


@router.patch("/me", response_model=UserRead)
async def update_current_user(
    update_data: UserUpdate,
    user: Annotated[User, Depends(get_required_user_with_dev_bypass)],
    user_manager: Annotated[UserManager, Depends(get_user_manager_dep)],
) -> User:
    """Update the current user's information.

    This endpoint supports DEV_MODE bypass - when DEV_MODE=true and
    DEV_USER_ID is set, allows updating the dev user without authentication.

    Args:
        update_data: Fields to update
        user: Current authenticated user (or dev user)
        user_manager: User manager for handling updates

    Returns:
        Updated user data

    Raises:
        HTTPException: 400 if username is already taken
    """
    try:
        updated_user = await user_manager.update(update_data, user)
        return updated_user
    except IntegrityError as e:
        # Check if this is a username conflict
        error_str = str(e).lower()
        if "username" in error_str or "unique" in error_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username is already taken. Please choose another.",
            ) from e
        # Re-raise other integrity errors
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Update failed due to a constraint violation.",
        ) from e


@router.get("/{user_id}", response_model=PublicUserRead)
async def get_public_user_profile(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> PublicUserRead:
    """Get public profile for any user.

    Returns user info excluding private fields (email, is_verified, etc.)

    Args:
        user_id: The user ID to look up

    Returns:
        Public user profile data

    Raises:
        HTTPException: 404 if user not found
    """
    repository = UserRepository(db)
    user = await repository.get_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return PublicUserRead(
        id=user.id,
        username=user.username,
        picture_url=user.picture_url,
        ratings=user.ratings or {},
        created_at=user.created_at,
        last_online=user.last_online,
    )


@router.get("/{user_id}/replays", response_model=ReplayListResponse)
async def get_user_replays(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
) -> ReplayListResponse:
    """Get paginated replays for a specific user.

    Uses the indexed user_game_history table for O(1) lookup performance.

    Args:
        user_id: The user ID
        limit: Maximum number of replays to return (1-50)
        offset: Number of replays to skip

    Returns:
        List of replay summaries with resolved player display names

    Raises:
        HTTPException: 404 if user not found
    """
    from kfchess.db.repositories.user_game_history import UserGameHistoryRepository

    # Verify user exists
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Use fast indexed user_game_history table (O(1) lookup)
    history_repo = UserGameHistoryRepository(db)
    history_entries = await history_repo.list_by_user(user_id, limit=limit, offset=offset)
    total = await history_repo.count_by_user(user_id)

    summaries = []
    for entry in history_entries:
        info = entry.game_info
        game_id = info.get("gameId") or info.get("historyId")

        # Build players dict: this user + opponents
        player_num = info.get("player", 1)
        players = {player_num: f"u:{user_id}"}
        opponents = info.get("opponents", [])
        # Get available slots (1-4 for 4-player, 1-2 for 2-player) excluding this player's slot
        max_players = 4 if len(opponents) > 1 else 2
        available_slots = [n for n in range(1, max_players + 1) if n != player_num]
        for i, opponent in enumerate(opponents):
            if i < len(available_slots):
                players[available_slots[i]] = opponent

        # Resolve player display names
        resolved_players = await resolve_player_names(db, players)

        summaries.append(
            ReplaySummary(
                game_id=str(game_id) if game_id else "unknown",
                speed=info.get("speed", "standard"),
                board_type=info.get("boardType", "standard"),
                players={str(k): v for k, v in resolved_players.items()},
                total_ticks=info.get("ticks", 0),
                winner=info.get("winner"),
                win_reason=info.get("winReason"),
                created_at=entry.game_time,
            )
        )

    return ReplayListResponse(replays=summaries, total=total)
