"""
User-related Pydantic schemas.

Includes: admin user CRUD, profile completion, expanded user response.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class AdminInviteUser(BaseModel):
    """Admin creates user by invite (name + email + phone, no CPF)."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(..., min_length=2, max_length=200)
    email: EmailStr
    phone: Optional[str] = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower().strip()


class AdminCreateUserDirect(BaseModel):
    """Admin creates user with direct password."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(..., min_length=2, max_length=200)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    is_admin: bool = False
    permissions: List[str] = []

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower().strip()


class AdminUpdateUser(BaseModel):
    """Admin updates user fields."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    is_admin: Optional[bool] = None
    permissions: Optional[List[str]] = None
    is_active: Optional[bool] = None
    new_password: Optional[str] = Field(default=None, min_length=8, max_length=128)


class AdminUserResponse(BaseModel):
    """Response for admin user listing."""

    id: int
    email: str
    name: Optional[str] = None
    is_admin: bool = False
    permissions: List[str] = []
    is_active: bool = True
    is_verified: bool = True


class UserProfileComplete(BaseModel):
    """User completes profile (CPF + address)."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    cpf: str = Field(..., pattern=r"^\d{3}\.?\d{3}\.?\d{3}-?\d{2}$")
    cep: str = Field(..., pattern=r"^\d{5}-?\d{3}$")
    logradouro: str = Field(..., min_length=2, max_length=255)
    numero: str = Field(..., min_length=1, max_length=20)
    complemento: Optional[str] = Field(None, max_length=100)
    bairro: str = Field(..., min_length=2, max_length=100)
    cidade: str = Field(..., min_length=2, max_length=100)
    uf: str = Field(..., pattern=r"^[A-Z]{2}$")


class UserResponseExpanded(BaseModel):
    """Expanded user response with profile_complete flag."""

    id: int
    email: str
    name: Optional[str] = None
    is_admin: bool = False
    permissions: List[str] = []
    is_active: bool = True
    is_verified: bool = True
    profile_complete: bool = False
