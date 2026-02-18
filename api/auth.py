"""
Authentication module
JWT-based authentication for the IconsAI Scraping API

SECURITY NOTES:
- Passwords are hashed using bcrypt (secure)
- SECRET_KEY must be set via environment variable
- Users are stored in Supabase database
"""

from datetime import datetime, timedelta
from typing import Optional

import bcrypt
import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from config.settings import settings

logger = structlog.get_logger()

# Configuration from settings (NOT hardcoded)
SECRET_KEY = settings.jwt_secret_key
ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

# Bearer token security
security = HTTPBearer()


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[int] = None
    role: Optional[str] = None
    permissions: Optional[list] = None


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    name: Optional[str]
    role: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None


def hash_password(password: str) -> str:
    """
    Hash password using bcrypt (secure).

    bcrypt automatically handles:
    - Salt generation
    - Multiple rounds of hashing
    - Protection against rainbow table attacks
    """
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against bcrypt hash.

    Returns True if password matches, False otherwise.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except Exception as e:
        logger.error("password_verify_error", error=str(e))
        return False


# Database-backed user authentication
async def get_user_from_db(email: str) -> Optional[dict]:
    """
    Get user from Supabase database.

    Falls back to legacy in-memory store if DB unavailable.
    """
    try:
        from src.database.client import get_supabase

        client = get_supabase()
        if client:
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
    except Exception as e:
        logger.warning("db_user_lookup_failed", error=str(e))

    # Fallback to legacy (for development/migration period)
    return _LEGACY_USERS_DB.get(email)


# Legacy in-memory store (DEPRECATED - use database)
# Keep temporarily for backwards compatibility during migration
# TODO: Remove after all users migrated to database
_LEGACY_USERS_DB = {
    "arbache@gmail.com": {
        "id": 1,
        "email": "arbache@gmail.com",
        # bcrypt hash for "admin123" - for development/testing
        "password_hash": "$2b$12$ne84FJ3BdgHPGhNnDQOC3OUZBQHbnStaDalq17VBnQXeX1/4.ZDMm",
        "name": "Fernando Arbache",
        "role": "super_admin",
        "permissions": ["empresas", "pessoas", "politicos", "noticias"],
    }
}


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def authenticate_user(email: str, password: str) -> Optional[dict]:
    """
    Authenticate user by email and password.

    1. Tries to get user from database
    2. Falls back to legacy in-memory store
    3. Verifies password using bcrypt
    """
    user = await get_user_from_db(email)
    if not user:
        logger.warning("auth_user_not_found", email=email)
        return None

    if not verify_password(password, user["password_hash"]):
        logger.warning("auth_invalid_password", email=email)
        return None

    logger.info("auth_success", email=email, role=user.get("role"))
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenData:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        role: str = payload.get("role")
        permissions: list = payload.get("permissions", [])
        if email is None:
            raise credentials_exception
        token_data = TokenData(
            email=email, user_id=user_id, role=role, permissions=permissions
        )
    except JWTError:
        raise credentials_exception
    return token_data


async def update_user(current_email: str, update_data: UserUpdate) -> Optional[dict]:
    """
    Update user data in database.

    Returns updated user or None if validation fails.
    """
    try:
        from src.database.client import get_supabase

        client = get_supabase()
        if not client:
            logger.warning("db_not_available_update_user")
            return await _update_user_legacy(current_email, update_data)

        # Get current user
        result = (
            client.table("users")
            .select("*")
            .eq("email", current_email)
            .limit(1)
            .execute()
        )

        if not result.data:
            return None

        user = result.data[0]
        updates = {"updated_at": datetime.utcnow().isoformat()}

        # Verify current password if changing password
        if update_data.new_password:
            if not update_data.current_password:
                return None
            if not verify_password(update_data.current_password, user["password_hash"]):
                return None
            updates["password_hash"] = hash_password(update_data.new_password)

        # Update name
        if update_data.name:
            updates["name"] = update_data.name

        # Update email
        if update_data.email and update_data.email != current_email:
            # Check if new email already exists
            existing = (
                client.table("users")
                .select("id")
                .eq("email", update_data.email)
                .execute()
            )
            if existing.data:
                return None
            updates["email"] = update_data.email

        # Apply updates
        result = (
            client.table("users").update(updates).eq("email", current_email).execute()
        )

        if result.data:
            logger.info("user_updated", email=current_email)
            return result.data[0]

    except Exception as e:
        logger.error("update_user_error", error=str(e))

    return None


async def _update_user_legacy(
    current_email: str, update_data: UserUpdate
) -> Optional[dict]:
    """
    Legacy update for in-memory store (DEPRECATED).
    """
    user = _LEGACY_USERS_DB.get(current_email)
    if not user:
        return None

    if update_data.new_password:
        if not update_data.current_password:
            return None
        if not verify_password(update_data.current_password, user["password_hash"]):
            return None
        user["password_hash"] = hash_password(update_data.new_password)

    if update_data.name:
        user["name"] = update_data.name

    if update_data.email and update_data.email != current_email:
        if update_data.email in _LEGACY_USERS_DB:
            return None
        _LEGACY_USERS_DB[update_data.email] = user
        user["email"] = update_data.email
        del _LEGACY_USERS_DB[current_email]

    return user
