"""
UploadSessionRepository — docs/ARCHITECTURE.md §4.
"""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.upload_session import UploadSession


class SqlUploadSessionRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, upload: UploadSession) -> UploadSession:
        self._session.add(upload)
        await self._session.flush()
        await self._session.refresh(upload)
        return upload

    async def get_by_id(self, session_id: str) -> UploadSession | None:
        return await self._session.get(UploadSession, session_id)

    async def list_by_user(self, user_id: str) -> list[UploadSession]:
        result = await self._session.execute(
            select(UploadSession)
            .where(UploadSession.user_id == user_id)
            .order_by(UploadSession.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_expired_pending(self, now: datetime) -> list[UploadSession]:
        result = await self._session.execute(
            select(UploadSession).where(
                UploadSession.status == "pending", UploadSession.expires_at < now
            )
        )
        return list(result.scalars().all())

    async def save(self, upload: UploadSession) -> UploadSession:
        await self._session.flush()
        return upload

