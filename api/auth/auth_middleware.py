"""
Auth middleware - FastAPI dependencies for authentication and authorization.
"""

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from api.auth.schemas.auth_schemas import TokenData
from config.settings import settings

logger = structlog.get_logger()

SECRET_KEY = settings.jwt_secret_key
ALGORITHM = settings.jwt_algorithm

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenData:
    """Dependency that extracts and validates the current user from JWT."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        token_type = payload.get("type", "access")
        if token_type != "access":
            raise credentials_exception

        email: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        name: str = payload.get("name")
        is_admin: bool = payload.get("is_admin", False)
        permissions: list = payload.get("permissions", [])
        if email is None:
            raise credentials_exception
        token_data = TokenData(
            email=email,
            user_id=user_id,
            name=name,
            is_admin=is_admin,
            permissions=permissions,
        )
    except JWTError:
        raise credentials_exception
    return token_data


def require_admin(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    """Dependency that requires is_admin == True."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Requer permissao de administrador.",
        )
    return current_user
