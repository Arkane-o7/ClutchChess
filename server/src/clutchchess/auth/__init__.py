"""Authentication module for Clutch Chess.

Provides user authentication using FastAPI-Users with support for:
- Email/password authentication
- Google OAuth
- Cookie-based JWT sessions
- DEV_MODE bypass for development
"""

from clutchchess.auth.backend import auth_backend
from clutchchess.auth.dependencies import (
    current_active_user,
    current_superuser,
    current_user,
    current_verified_user,
    fastapi_users,
    get_current_user_with_dev_bypass,
    get_required_user_with_dev_bypass,
    optional_current_user,
)
from clutchchess.auth.router import get_auth_router
from clutchchess.auth.schemas import UserCreate, UserRead, UserUpdate
from clutchchess.auth.users import UserManager, generate_random_username

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
