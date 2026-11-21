"""
Schemas User Management (CR v3.7, 21 Nov 2026) — docs/ARCHITECTURE.md §5.

Hanya profil + role; password dikelola Supabase Auth (bukan lewat API ini).
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

# Sama dengan app.models.user.VALID_ROLES (FR-8.1).
Role = Literal["admin", "ppic", "purchasing", "viewer"]


def _strip(value: str | None) -> str | None:
    return value.strip() if isinstance(value, str) else value


class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=100)
    role: Role

    _strip_name = field_validator("name", mode="before")(_strip)


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    role: Role | None = None
    is_active: bool | None = None

    _strip_name = field_validator("name", mode="before")(_strip)


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    role: str
    is_verified: bool
    is_active: bool
    created_at: datetime | None = None
