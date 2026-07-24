"""
UserRepository — akses tabel `users` (docs/ARCHITECTURE.md §4).

Dipisah dari service supaya AuthService bisa diuji dengan repo in-memory palsu
tanpa DB nyata (lihat tests/unit/test_auth_service.py).
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class SqlUserRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: str) -> User | None:
        return await self._session.get(User, user_id)
