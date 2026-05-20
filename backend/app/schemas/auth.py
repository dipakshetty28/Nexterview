from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import UserRole


class OrganizationRead(BaseModel):
    id: UUID
    name: str
    slug: str

    model_config = ConfigDict(from_attributes=True)


class OrganizationMembershipRead(BaseModel):
    role: UserRole
    organization: OrganizationRead

    model_config = ConfigDict(from_attributes=True)


class UserRead(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    organizations: list[OrganizationMembershipRead] = Field(default_factory=list)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=72)
    full_name: str = Field(min_length=2, max_length=120)
    organization_name: str = Field(min_length=2, max_length=160)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, password: str) -> str:
        has_letter = any(character.isalpha() for character in password)
        has_number = any(character.isdigit() for character in password)
        if not has_letter or not has_number:
            raise ValueError("Password must include at least one letter and one number.")
        return password


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class TokenPayload(BaseModel):
    sub: UUID
    exp: int
