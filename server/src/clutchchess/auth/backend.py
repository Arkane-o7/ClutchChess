"""Authentication backend configuration.

Sets up cookie-based JWT authentication for the application.
"""

from fastapi_users.authentication import AuthenticationBackend, CookieTransport, JWTStrategy

from clutchchess.settings import get_settings

# Get settings at module load time for cookie configuration
_settings = get_settings()

# Cookie transport configuration
# Uses httponly cookies for security (not accessible via JavaScript)
# cookie_secure is True in production (when dev_mode is False) to ensure
# cookies are only sent over HTTPS
cookie_transport = CookieTransport(
    cookie_name="clutchchess_auth",
    cookie_max_age=3600 * 24 * 30,  # 30 days
    cookie_secure=not _settings.dev_mode,  # Secure in production, not in dev
    cookie_httponly=True,
    cookie_samesite="lax",
)


def get_jwt_strategy() -> JWTStrategy:
    """Get the JWT strategy for authentication.

    Returns:
        JWT strategy configured with secret and lifetime
    """
    settings = get_settings()
    return JWTStrategy(
        secret=settings.secret_key,
        lifetime_seconds=3600 * 24 * 30,  # 30 days
    )


# The authentication backend combines transport and strategy
auth_backend = AuthenticationBackend(
    name="cookie",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)
