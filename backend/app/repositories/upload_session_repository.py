"""
UploadSessionRepository & ConsumptionHistoryRepository — docs/ARCHITECTURE.md §4.
"""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consumption_history import ConsumptionHistory
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


class SqlConsumptionHistoryRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def bulk_add(self, rows: list[ConsumptionHistory]) -> int:
        self._session.add_all(rows)
        await self._session.flush()
        return len(rows)

    async def list_for_material(self, material_id: str, material_code: str) -> list[ConsumptionHistory]:
        """Ambil histori konsumsi satu material — cocokkan lewat id ATAU code.

        Sebagian baris bisa punya material_id null (diupload sebelum material
        terdaftar, RECONCILIATION #14), jadi code dipakai sebagai jaring pengaman.
        """
        result = await self._session.execute(
            select(ConsumptionHistory)
            .where(
                (ConsumptionHistory.material_id == material_id)
                | (ConsumptionHistory.material_code == material_code)
            )
            .order_by(ConsumptionHistory.date)
        )
        return list(result.scalars().all())
