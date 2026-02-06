#!/usr/bin/env python
"""Seed a development user for DEV_MODE testing.

This script creates a user with a known ID that can be used with
DEV_MODE=true and DEV_USER_ID=1 for local development.

Usage:
    cd server
    uv run python scripts/seed_dev_user.py

The script is idempotent - running it multiple times is safe.
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to the path so we can import clutchchess
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from clutchchess.db.models import User
from clutchchess.db.session import async_session_factory, engine


DEV_USER_ID = 1
DEV_USER_EMAIL = "dev@clutchchess.local"
DEV_USER_USERNAME = "DevUser"
DEV_USER_PASSWORD_HASH = (
    # Hash of "devpassword123" - for local testing only
    "$argon2id$v=19$m=65536,t=3,p=4$"
    "c29tZXNhbHQ$"
    "VGhlIHF1aWNrIGJyb3duIGZveCBqdW1wcyBvdmVyIHRoZSBsYXp5IGRvZw"
)


async def seed_dev_user() -> None:
    """Create or update the development user."""
    async with async_session_factory() as session:
        # Check if user already exists
        existing = await session.get(User, DEV_USER_ID)

        if existing:
            print(f"Dev user already exists: {existing.username} (ID: {existing.id})")
            print("No changes made.")
            return

        # Create the dev user
        dev_user = User(
            id=DEV_USER_ID,
            email=DEV_USER_EMAIL,
            username=DEV_USER_USERNAME,
            hashed_password=DEV_USER_PASSWORD_HASH,
            is_active=True,
            is_verified=True,
            is_superuser=True,
        )

        session.add(dev_user)
        await session.commit()

        print(f"Created dev user:")
        print(f"  ID:       {DEV_USER_ID}")
        print(f"  Email:    {DEV_USER_EMAIL}")
        print(f"  Username: {DEV_USER_USERNAME}")
        print()
        print("To use DEV_MODE, set these environment variables:")
        print("  DEV_MODE=true")
        print(f"  DEV_USER_ID={DEV_USER_ID}")


async def reset_sequence() -> None:
    """Reset the user ID sequence to avoid conflicts."""
    async with engine.begin() as conn:
        # Ensure the sequence is ahead of any manually inserted IDs
        await conn.execute(
            text("SELECT setval('users_id_seq', GREATEST(COALESCE((SELECT MAX(id) FROM users), 0), 1))")
        )


async def main() -> None:
    """Main entry point."""
    print("Seeding development user...")
    print()

    try:
        await seed_dev_user()
        await reset_sequence()
        print()
        print("Done!")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
