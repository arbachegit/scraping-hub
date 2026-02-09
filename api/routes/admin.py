"""
Admin Routes - User Management
Only accessible by super_admin role
"""

from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from api.auth import TokenData, get_current_user, hash_password
from src.database.client import get_supabase

logger = structlog.get_logger()

router = APIRouter(prefix="/admin", tags=["Admin"])

# ===========================================
# Models
# ===========================================

VALID_AREAS = ["empresas", "pessoas", "politicos", "noticias"]
VALID_ROLES = ["super_admin", "admin", "user"]


class UserCreate(BaseModel):
    """Schema for creating a new user"""

    email: EmailStr
    password: str = Field(..., min_length=6)
    name: str = Field(..., min_length=2)
    role: str = Field(default="user")
    permissions: List[str] = Field(default=[])

    class Config:
        json_schema_extra = {
            "example": {
                "email": "usuario@empresa.com",
                "password": "senha123",
                "name": "Nome do Usuario",
                "role": "user",
                "permissions": ["empresas", "pessoas"],
            }
        }


class UserUpdate(BaseModel):
    """Schema for updating a user"""

    name: Optional[str] = None
    role: Optional[str] = None
    permissions: Optional[List[str]] = None
    is_active: Optional[bool] = None
    new_password: Optional[str] = Field(None, min_length=6)


class UserResponse(BaseModel):
    """Schema for user response"""

    id: int
    email: str
    name: Optional[str]
    role: str
    permissions: List[str]
    is_active: bool


class UserListResponse(BaseModel):
    """Schema for list of users"""

    users: List[UserResponse]
    total: int


# ===========================================
# Dependency: Super Admin Check
# ===========================================


async def require_super_admin(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    """Require super_admin role for access"""
    if current_user.role != "super_admin":
        logger.warning("admin_access_denied", email=current_user.email, role=current_user.role)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas super_admin pode acessar esta area.",
        )
    return current_user


# ===========================================
# Endpoints
# ===========================================


@router.get("/users", response_model=UserListResponse)
async def list_users(
    current_user: TokenData = Depends(require_super_admin),
    skip: int = 0,
    limit: int = 50,
):
    """
    List all users (super_admin only)

    Returns list of users with their permissions.
    """
    client = get_supabase()
    if not client:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        # Get users with pagination
        result = (
            client.table("users")
            .select("id, email, name, role, permissions, is_active")
            .order("created_at", desc=True)
            .range(skip, skip + limit - 1)
            .execute()
        )

        # Get total count
        count_result = client.table("users").select("id", count="exact").execute()
        total = count_result.count if count_result.count else len(result.data)

        users = []
        for user in result.data:
            users.append(
                UserResponse(
                    id=user["id"],
                    email=user["email"],
                    name=user.get("name"),
                    role=user.get("role", "user"),
                    permissions=user.get("permissions") or [],
                    is_active=user.get("is_active", True),
                )
            )

        logger.info("admin_list_users", admin=current_user.email, count=len(users))
        return UserListResponse(users=users, total=total)

    except Exception as e:
        logger.error("admin_list_users_error", error=str(e))
        raise HTTPException(status_code=500, detail="Erro ao listar usuarios")


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: TokenData = Depends(require_super_admin),
):
    """
    Create a new user (super_admin only)

    - **email**: User email (must be unique)
    - **password**: Password (min 6 characters)
    - **name**: Display name
    - **role**: user, admin, or super_admin
    - **permissions**: List of areas (empresas, pessoas, politicos, noticias)
    """
    client = get_supabase()
    if not client:
        raise HTTPException(status_code=503, detail="Database not available")

    # Validate role
    if user_data.role not in VALID_ROLES:
        raise HTTPException(
            status_code=400, detail=f"Role invalido. Use: {', '.join(VALID_ROLES)}"
        )

    # Validate permissions
    invalid_perms = [p for p in user_data.permissions if p not in VALID_AREAS]
    if invalid_perms:
        raise HTTPException(
            status_code=400,
            detail=f"Permissoes invalidas: {invalid_perms}. Use: {', '.join(VALID_AREAS)}",
        )

    # super_admin always has all permissions
    if user_data.role == "super_admin":
        user_data.permissions = VALID_AREAS.copy()

    try:
        # Check if email already exists
        existing = client.table("users").select("id").eq("email", user_data.email).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Email ja cadastrado")

        # Hash password
        password_hash = hash_password(user_data.password)

        # Insert user
        result = (
            client.table("users")
            .insert(
                {
                    "email": user_data.email,
                    "password_hash": password_hash,
                    "name": user_data.name,
                    "role": user_data.role,
                    "permissions": user_data.permissions,
                    "is_active": True,
                }
            )
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=500, detail="Erro ao criar usuario")

        new_user = result.data[0]
        logger.info(
            "admin_create_user",
            admin=current_user.email,
            new_user=user_data.email,
            role=user_data.role,
        )

        return UserResponse(
            id=new_user["id"],
            email=new_user["email"],
            name=new_user.get("name"),
            role=new_user.get("role", "user"),
            permissions=new_user.get("permissions") or [],
            is_active=new_user.get("is_active", True),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("admin_create_user_error", error=str(e))
        raise HTTPException(status_code=500, detail="Erro ao criar usuario")


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: TokenData = Depends(require_super_admin),
):
    """Get a specific user by ID (super_admin only)"""
    client = get_supabase()
    if not client:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        result = (
            client.table("users")
            .select("id, email, name, role, permissions, is_active")
            .eq("id", user_id)
            .single()
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Usuario nao encontrado")

        user = result.data
        return UserResponse(
            id=user["id"],
            email=user["email"],
            name=user.get("name"),
            role=user.get("role", "user"),
            permissions=user.get("permissions") or [],
            is_active=user.get("is_active", True),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("admin_get_user_error", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="Erro ao buscar usuario")


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: TokenData = Depends(require_super_admin),
):
    """
    Update a user (super_admin only)

    Can update: name, role, permissions, is_active, password
    """
    client = get_supabase()
    if not client:
        raise HTTPException(status_code=503, detail="Database not available")

    # Validate role if provided
    if user_data.role and user_data.role not in VALID_ROLES:
        raise HTTPException(
            status_code=400, detail=f"Role invalido. Use: {', '.join(VALID_ROLES)}"
        )

    # Validate permissions if provided
    if user_data.permissions:
        invalid_perms = [p for p in user_data.permissions if p not in VALID_AREAS]
        if invalid_perms:
            raise HTTPException(
                status_code=400,
                detail=f"Permissoes invalidas: {invalid_perms}. Use: {', '.join(VALID_AREAS)}",
            )

    try:
        # Check if user exists
        existing = (
            client.table("users")
            .select("id, email, role")
            .eq("id", user_id)
            .single()
            .execute()
        )

        if not existing.data:
            raise HTTPException(status_code=404, detail="Usuario nao encontrado")

        # Prevent self-demotion from super_admin
        if (
            existing.data["email"] == current_user.email
            and user_data.role
            and user_data.role != "super_admin"
        ):
            raise HTTPException(
                status_code=400, detail="Voce nao pode remover seu proprio role de super_admin"
            )

        # Build update dict
        updates = {}
        if user_data.name is not None:
            updates["name"] = user_data.name
        if user_data.role is not None:
            updates["role"] = user_data.role
            # super_admin always has all permissions
            if user_data.role == "super_admin":
                updates["permissions"] = VALID_AREAS.copy()
        if user_data.permissions is not None and user_data.role != "super_admin":
            updates["permissions"] = user_data.permissions
        if user_data.is_active is not None:
            updates["is_active"] = user_data.is_active
        if user_data.new_password:
            updates["password_hash"] = hash_password(user_data.new_password)

        if not updates:
            raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

        # Update user
        result = client.table("users").update(updates).eq("id", user_id).execute()

        if not result.data:
            raise HTTPException(status_code=500, detail="Erro ao atualizar usuario")

        user = result.data[0]
        logger.info(
            "admin_update_user",
            admin=current_user.email,
            updated_user_id=user_id,
            updates=list(updates.keys()),
        )

        return UserResponse(
            id=user["id"],
            email=user["email"],
            name=user.get("name"),
            role=user.get("role", "user"),
            permissions=user.get("permissions") or [],
            is_active=user.get("is_active", True),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("admin_update_user_error", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="Erro ao atualizar usuario")


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: TokenData = Depends(require_super_admin),
):
    """
    Delete a user (super_admin only)

    Note: This is a soft delete (sets is_active=false)
    """
    client = get_supabase()
    if not client:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        # Check if user exists
        existing = (
            client.table("users").select("id, email").eq("id", user_id).single().execute()
        )

        if not existing.data:
            raise HTTPException(status_code=404, detail="Usuario nao encontrado")

        # Prevent self-deletion
        if existing.data["email"] == current_user.email:
            raise HTTPException(status_code=400, detail="Voce nao pode deletar a si mesmo")

        # Soft delete (deactivate)
        client.table("users").update({"is_active": False}).eq("id", user_id).execute()

        logger.info(
            "admin_delete_user",
            admin=current_user.email,
            deleted_user_id=user_id,
            deleted_email=existing.data["email"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("admin_delete_user_error", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="Erro ao deletar usuario")


@router.get("/areas")
async def list_areas(current_user: TokenData = Depends(require_super_admin)):
    """
    List available areas/permissions

    Returns the valid areas that can be assigned to users.
    """
    return {
        "areas": VALID_AREAS,
        "roles": VALID_ROLES,
        "description": {
            "empresas": "Acesso a analise de empresas e CNPJ",
            "pessoas": "Acesso a analise de pessoas e perfis",
            "politicos": "Acesso a analise de politicos",
            "noticias": "Acesso a monitoramento de noticias",
        },
    }
