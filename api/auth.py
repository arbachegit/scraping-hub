"""
Authentication module
JWT-based authentication for the IconsAI Scraping API
"""

import hashlib
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

# Configuration
SECRET_KEY = "iconsai-scraping-secret-key-change-in-production-2024"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

# Bearer token security
security = HTTPBearer()


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[int] = None
    role: Optional[str] = None


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
    """Simple SHA256 hash for password"""
    return hashlib.sha256(password.encode()).hexdigest()


# In-memory user store
USERS_DB = {
    "arbache@gmail.com": {
        "id": 1,
        "email": "arbache@gmail.com",
        "password_hash": hash_password("6GjCJKBXJXbells"),
        "name": "Fernando Arbache",
        "role": "admin"
    }
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def authenticate_user(email: str, password: str) -> Optional[dict]:
    user = USERS_DB.get(email)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
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
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email, user_id=user_id, role=role)
    except JWTError:
        raise credentials_exception
    return token_data


def update_user(
    current_email: str,
    update_data: UserUpdate
) -> Optional[dict]:
    """
    Update user data in the in-memory store

    Returns updated user or None if validation fails
    """
    user = USERS_DB.get(current_email)
    if not user:
        return None

    # Verify current password if changing password
    if update_data.new_password:
        if not update_data.current_password:
            return None
        if not verify_password(update_data.current_password, user["password_hash"]):
            return None
        user["password_hash"] = hash_password(update_data.new_password)

    # Update name
    if update_data.name:
        user["name"] = update_data.name

    # Update email (requires re-keying the dict)
    if update_data.email and update_data.email != current_email:
        # Check if new email already exists
        if update_data.email in USERS_DB:
            return None
        # Move user to new email key
        USERS_DB[update_data.email] = user
        user["email"] = update_data.email
        del USERS_DB[current_email]

    return user
