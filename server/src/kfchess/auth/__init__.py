"""Authentication module for Kung Fu Chess.

Provides user authentication using FastAPI-Users with support for:
- Email/password authentication
- Google OAuth
- Cookie-based JWT sessions
- DEV_MODE bypass for development
"""

from kfchess.auth.backend import auth_backend
from kfchess.auth.dependencies import (
    current_active_user,
    current_superuser,
    current_user,
    current_verified_user,
    fastapi_users,
    get_current_user_with_dev_bypass,
    get_required_user_with_dev_bypass,
    optional_current_user,
)
from kfchess.auth.router import get_auth_router
from kfchess.auth.schemas import UserCreate, UserRead, UserUpdate
from kfchess.auth.users import UserManager, generate_random_username

__all__ = [
    # Backend
    "auth_backend",
    # FastAPIUsers instance
    "fastapi_users",
    # Dependencies
    "current_user",
    "current_active_user",
    "current_verified_user",
    "current_superuser",
    "optional_current_user",
    "get_current_user_with_dev_bypass",
    "get_required_user_with_dev_bypass",
    # Router
    "get_auth_router",
    # Schemas
    "UserRead",
    "UserCreate",
    "UserUpdate",
    # User Manager
    "UserManager",
    "generate_random_username",
]
