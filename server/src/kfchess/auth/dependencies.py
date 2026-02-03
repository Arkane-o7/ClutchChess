"""FastAPI-Users dependencies and configuration.

Provides the FastAPIUsers instance and dependency functions for
getting current user, with DEV_MODE bypass support.
"""

import logging
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi_users import FastAPIUsers
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from kfchess.auth.backend import auth_backend
from kfchess.auth.users import UserManager
from kfchess.db import session as db_session
from kfchess.db.models import OAuthAccount, User
from kfchess.db.repositories.users import UserRepository
from kfchess.db.session import get_db_session
from kfchess.settings import get_settings


async def get_user_db(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AsyncGenerator[SQLAlchemyUserDatabase[User, int], None]:
    """Get the user database adapter.

    Args:
        session: The database session (injected)

    Yields:
        SQLAlchemy user database adapter
    """
    yield SQLAlchemyUserDatabase(session, User, OAuthAccount)


async def get_user_manager_dep(
    user_db: Annotated[SQLAlchemyUserDatabase[User, int], Depends(get_user_db)],
) -> AsyncGenerator[UserManager, None]:
    """Get the user manager dependency.

    Args:
        user_db: The user database adapter (injected)

    Yields:
        UserManager instance
    """
    yield UserManager(user_db)


# Create the FastAPIUsers instance
fastapi_users = FastAPIUsers[User, int](
    get_user_manager_dep,
    [auth_backend],
)

# Standard FastAPI-Users dependencies
current_user = fastapi_users.current_user()
current_active_user = fastapi_users.current_user(active=True)
current_verified_user = fastapi_users.current_user(active=True, verified=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)

# Optional user (doesn't require authentication)
optional_current_user = fastapi_users.current_user(optional=True)


async def get_current_user_with_dev_bypass(
    request: Request,
    user: Annotated[User | None, Depends(optional_current_user)],
) -> User | None:
    """Get current user with DEV_MODE bypass.

    In DEV_MODE with DEV_USER_ID set, and when no user is authenticated,
    automatically returns the dev user. This is useful for local development.

    If a user IS authenticated, they are returned regardless of DEV_MODE,
    allowing developers to test as different users.

    Args:
        request: The FastAPI request
        user: The authenticated user (if any) from normal auth flow

    Returns:
        The authenticated user, dev user (if no auth and DEV_MODE), or None
    """
    logger = logging.getLogger(__name__)

    # If user is already authenticated, return them (don't override)
    if user is not None:
        return user

    # Only use dev bypass when no user is authenticated
    settings = get_settings()
    if settings.dev_mode and settings.dev_user_id is not None:
        async with db_session.async_session_factory() as session:
            repo = UserRepository(session)
            dev_user = await repo.get_by_id(settings.dev_user_id)
            if dev_user:
                logger.debug(f"DEV_MODE: Using dev user {dev_user.id} ({dev_user.username})")
                return dev_user

    return None


async def get_required_user_with_dev_bypass(
    request: Request,
    user: Annotated[User | None, Depends(optional_current_user)],
) -> User:
    """Get current user with DEV_MODE bypass, requiring authentication.

    Same as get_current_user_with_dev_bypass but raises 401 if no user.

    Args:
        request: The FastAPI request
        user: The authenticated user (if any) from normal auth flow

    Returns:
        The authenticated user or dev user

    Raises:
        HTTPException: If no user is authenticated and DEV_MODE is off
    """
    result = await get_current_user_with_dev_bypass(request, user)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return result
