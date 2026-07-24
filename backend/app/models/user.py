"""
ORM model `users` — docs/ARCHITECTURE.md §4.

Profil + role user. Kredensial (password) TIDAK disimpan di sini — itu dikelola
Supabase Auth (GoTrue). Tabel ini hanya mirror profil + role untuk RBAC (FR-8).
`id` diselaraskan dengan `auth.users.id` milik Supabase.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Role valid (FR-8.1) — dipakai juga oleh RBAC dependency (app/api/deps.py).
VALID_ROLES = ("admin", "ppic", "purchasing", "viewer")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="viewer")
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
