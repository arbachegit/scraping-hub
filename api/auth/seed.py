"""
Seed user via environment variables.

Creates the initial user on startup if:
- SEED_ADMIN_EMAIL and SEED_ADMIN_PASSWORD are set
- No user with that email exists yet
"""

import structlog

from api.auth.auth_service import hash_password
from config.settings import settings
from src.database.client import get_supabase

logger = structlog.get_logger()


async def seed_super_admin() -> None:
    """
    Create seed user from environment variables (idempotent).

    Reads SEED_ADMIN_EMAIL, SEED_ADMIN_PASSWORD, SEED_ADMIN_NAME from settings.
    Only creates if user does not already exist.
    """
    if not settings.seed_admin_email or not settings.seed_admin_password:
        logger.info("seed_user_skipped", reason="SEED_ADMIN_EMAIL or SEED_ADMIN_PASSWORD not set")
        return

    client = get_supabase()
    if not client:
        logger.warning("seed_user_no_db", reason="Supabase not configured")
        return

    try:
        # Check if user already exists
        existing = (
            client.table("users")
            .select("id")
            .eq("email", settings.seed_admin_email.lower())
            .limit(1)
            .execute()
        )

        if existing.data:
            logger.info(
                "seed_user_exists",
                email=settings.seed_admin_email,
                msg="Seed user already exists, skipping.",
            )
            return

        # Create seed user (no special privileges)
        new_user = {
            "email": settings.seed_admin_email.lower(),
            "name": settings.seed_admin_name,
            "password_hash": hash_password(settings.seed_admin_password),
            "permissions": ["empresas", "pessoas", "politicos", "noticias"],
            "is_active": True,
            "is_verified": True,
        }

        result = client.table("users").insert(new_user).execute()

        if result.data:
            logger.info(
                "seed_user_created",
                email=settings.seed_admin_email,
                msg="Seed user created successfully.",
            )
        else:
            logger.error("seed_user_insert_failed", email=settings.seed_admin_email)

    except Exception as e:
        logger.error("seed_user_error", error=str(e))
