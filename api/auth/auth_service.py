"""
Authentication service.

JWT creation/validation, password hashing/verification, token management.
Extracted from the original api/auth.py.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import structlog
from jose import JWTError, jwt

from api.auth.schemas.auth_schemas import UserUpdate
from config.settings import settings

logger = structlog.get_logger()

# Configuration from settings (NOT hardcoded)
SECRET_KEY = settings.jwt_secret_key
ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = settings.refresh_token_expire_days


def hash_password(password: str) -> str:
    """Hash password using bcrypt (12 rounds)."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception as e:
        logger.error("password_verify_error", error=str(e))
        return False


async def get_user_from_db(email: str) -> Optional[dict]:
    """Get user from Supabase database."""
    try:
        from src.database.client import get_supabase

        client = get_supabase()
        if not client:
            logger.error("get_user_no_supabase", msg="Supabase client is None. Check SUPABASE_URL and SUPABASE_SERVICE_KEY.")
            return None

        result = (
            client.table("users")
            .select("*")
            .eq("email", email)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )

        if result.data:
            logger.info("user_found_db", email=email)
            return result.data[0]

        logger.info("user_not_found_db", email=email)
    except Exception as e:
        logger.error("db_user_lookup_failed", email=email, error=str(e), error_type=type(e).__name__)

    return None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_set_password_token(user_id: int, email: str) -> str:
    """Create a JWT token for setting the initial password. Valid for 24 hours."""
    expire = datetime.now(timezone.utc) + timedelta(hours=24)
    to_encode = {
        "sub": email,
        "user_id": user_id,
        "type": "set_password",
        "exp": expire,
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_password_reset_token(user_id: int, email: str) -> str:
    """Create a JWT token for password reset. Valid for 1 hour."""
    expire = datetime.now(timezone.utc) + timedelta(hours=1)
    to_encode = {
        "sub": email,
        "user_id": user_id,
        "type": "password_reset",
        "exp": expire,
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def create_refresh_token(user_id: int) -> Optional[str]:
    """Create a refresh token and store its hash in the database."""
    from src.database.client import get_supabase

    raw_token = secrets.token_urlsafe(64)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    expires_at = (
        datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    ).isoformat()

    client = get_supabase()
    if not client:
        logger.warning("refresh_token_no_db")
        return None

    try:
        client.table("refresh_tokens").insert(
            {
                "user_id": user_id,
                "token_hash": token_hash,
                "expires_at": expires_at,
            }
        ).execute()
        logger.info("refresh_token_created", user_id=user_id)
        return raw_token
    except Exception as e:
        logger.error("refresh_token_store_failed", error=str(e))
        return None


async def validate_refresh_token(raw_token: str) -> Optional[dict]:
    """Validate a refresh token and return the associated user."""
    from src.database.client import get_supabase

    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc).isoformat()

    client = get_supabase()
    if not client:
        return None

    try:
        result = (
            client.table("refresh_tokens")
            .select("*")
            .eq("token_hash", token_hash)
            .is_("revoked_at", "null")
            .gte("expires_at", now)
            .limit(1)
            .execute()
        )

        if not result.data:
            logger.warning("refresh_token_invalid")
            return None

        token_row = result.data[0]
        user_id = token_row["user_id"]

        # Revoke the used refresh token (rotation)
        client.table("refresh_tokens").update(
            {"revoked_at": now}
        ).eq("id", token_row["id"]).execute()

        # Get user
        user_result = (
            client.table("users")
            .select("*")
            .eq("id", user_id)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )

        if not user_result.data:
            return None

        return user_result.data[0]

    except Exception as e:
        logger.error("refresh_token_validate_failed", error=str(e))
        return None


def decode_special_token(token: str, expected_type: str) -> Optional[dict]:
    """Decode a special-purpose JWT (set_password, password_reset)."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != expected_type:
            logger.warning("token_type_mismatch", expected=expected_type, got=payload.get("type"))
            return None
        return payload
    except JWTError as e:
        logger.warning("special_token_decode_failed", error=str(e))
        return None


async def authenticate_user(email: str, password: str) -> Optional[dict]:
    """Authenticate user by email and password."""
    user = await get_user_from_db(email.lower().strip())
    if not user:
        logger.warning("auth_user_not_found", email=email)
        return None

    if not verify_password(password, user["password_hash"]):
        logger.warning("auth_invalid_password", email=email)
        return None

    logger.info("auth_success", email=email, is_admin=user.get("is_admin", False))
    return user


async def update_user(current_email: str, update_data: UserUpdate) -> Optional[dict]:
    """Update user data in database."""
    try:
        from src.database.client import get_supabase

        client = get_supabase()
        if not client:
            logger.warning("db_not_available_update_user")
            return None

        result = client.table("users").select("*").eq("email", current_email).limit(1).execute()

        if not result.data:
            return None

        user = result.data[0]
        updates = {"updated_at": datetime.now(timezone.utc).isoformat()}

        if update_data.new_password:
            if not update_data.current_password:
                return None
            if not verify_password(update_data.current_password, user["password_hash"]):
                return None
            updates["password_hash"] = hash_password(update_data.new_password)

        if update_data.name:
            updates["name"] = update_data.name

        if update_data.email and update_data.email != current_email:
            existing = client.table("users").select("id").eq("email", update_data.email).execute()
            if existing.data:
                return None
            updates["email"] = update_data.email

        result = client.table("users").update(updates).eq("email", current_email).execute()

        if result.data:
            logger.info("user_updated", email=current_email)
            return result.data[0]

    except Exception as e:
        logger.error("update_user_error", error=str(e))

    return None
