"""
UserRepository — akses tabel `users` (docs/ARCHITECTURE.md §4).

Dipisah dari service supaya AuthService bisa diuji dengan repo in-memory palsu
tanpa DB nyata (lihat tests/unit/test_auth_service.py).
"""
# Kelas punya method `list` → tanpa ini anotasi list[...] rusak di Python 3.11 (VPS).
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class SqlUserRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_email(self, email: str) -> User | None:
        # Tidak peka huruf besar (CR v3.7): profil baru disimpan lowercase, profil lama bisa
        # saja diinsert manual dengan huruf besar (DEPLOYMENT.md §"user pertama").
        result = await self._session.execute(select(User).where(func.lower(User.email) == email.strip().lower()))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: str) -> User | None:
        return await self._session.get(User, user_id)

    async def list(self) -> list[User]:
        result = await self._session.execute(select(User).order_by(User.email))
        return list(result.scalars().all())

    async def create(self, *, email: str, name: str, role: str, is_verified: bool) -> User:
        """Dipakai seeding user dev (app/scripts/seed_dev_users.py) dan User Management (CR v3.7).

        Akun login (password) tetap dibuat di Supabase Auth, bukan lewat sini.
        """
        user = User(email=email, name=name, role=role, is_verified=is_verified)
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def save(self, user: User) -> User:
        await self._session.flush()
        await self._session.refresh(user)
        return user
