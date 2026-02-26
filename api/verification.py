"""
Verification code service.

Generates and validates 6-digit codes for account activation
and password recovery flows.

Codes are:
- 6 digits (000000-999999)
- Hashed with SHA-256 before storage
- Valid for 10 minutes
- Max 5 attempts per hour per user
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

import structlog

from src.database.client import get_supabase

logger = structlog.get_logger()

CODE_EXPIRY_MINUTES = 10
MAX_CODES_PER_HOUR = 5


def generate_code() -> Tuple[str, str]:
    """
    Generate a 6-digit verification code.

    Returns:
        Tuple of (code_plain, code_hash).
        code_plain: The 6-digit string to send to the user.
        code_hash: SHA-256 hash to store in the database.
    """
    code = f"{secrets.randbelow(1000000):06d}"
    code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
    return code, code_hash


def hash_code(code: str) -> str:
    """Hash a verification code with SHA-256."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


async def create_verification_code(
    user_id: int, code_type: str
) -> Optional[str]:
    """
    Create and store a verification code for a user.

    Enforces rate limiting (max 5 codes per hour).

    Args:
        user_id: The user's ID.
        code_type: Either 'activation' or 'password_reset'.

    Returns:
        The plain 6-digit code, or None if rate limited.
    """
    client = get_supabase()
    if not client:
        logger.error("verification_code_no_db")
        return None

    # Rate limit check: max codes per hour
    one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    try:
        recent = (
            client.table("verification_codes")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .eq("type", code_type)
            .gte("created_at", one_hour_ago)
            .execute()
        )
        if (recent.count or 0) >= MAX_CODES_PER_HOUR:
            logger.warning(
                "verification_rate_limited",
                user_id=user_id,
                type=code_type,
            )
            return None
    except Exception as e:
        logger.warning("verification_rate_check_failed", error=str(e))

    # Generate code
    code_plain, code_hashed = generate_code()
    expires_at = (
        datetime.now(timezone.utc) + timedelta(minutes=CODE_EXPIRY_MINUTES)
    ).isoformat()

    # Store
    try:
        client.table("verification_codes").insert(
            {
                "user_id": user_id,
                "code_hash": code_hashed,
                "type": code_type,
                "expires_at": expires_at,
            }
        ).execute()
        logger.info("verification_code_created", user_id=user_id, type=code_type)
        return code_plain
    except Exception as e:
        logger.error("verification_code_store_failed", error=str(e))
        return None


async def verify_code(
    user_id: int, code: str, code_type: str
) -> bool:
    """
    Verify a submitted code against stored hashes.

    Checks the most recent unused, non-expired code of the given type.

    Args:
        user_id: The user's ID.
        code: The 6-digit code submitted by the user.
        code_type: Either 'activation' or 'password_reset'.

    Returns:
        True if code is valid, False otherwise.
    """
    client = get_supabase()
    if not client:
        logger.error("verify_code_no_db")
        return False

    submitted_hash = hash_code(code)
    now = datetime.now(timezone.utc).isoformat()

    try:
        result = (
            client.table("verification_codes")
            .select("*")
            .eq("user_id", user_id)
            .eq("type", code_type)
            .eq("code_hash", submitted_hash)
            .is_("used_at", "null")
            .gte("expires_at", now)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if not result.data:
            logger.warning(
                "verification_code_invalid",
                user_id=user_id,
                type=code_type,
            )
            return False

        # Mark code as used
        code_id = result.data[0]["id"]
        client.table("verification_codes").update(
            {"used_at": now}
        ).eq("id", code_id).execute()

        logger.info("verification_code_verified", user_id=user_id, type=code_type)
        return True

    except Exception as e:
        logger.error("verify_code_error", error=str(e))
        return False
