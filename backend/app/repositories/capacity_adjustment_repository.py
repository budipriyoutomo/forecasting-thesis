"""
CapacityAdjustment repository (Fase 11.17) — append-only, tidak pernah update/delete.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capacity_adjustment import CapacityAdjustment


class SqlCapacityAdjustmentRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add_all(self, rows: list[CapacityAdjustment]) -> list[CapacityAdjustment]:
        self._session.add_all(rows)
        await self._session.flush()
        for row in rows:
            await self._session.refresh(row)
        return rows

    async def list_by_run(self, run_id: str) -> list[CapacityAdjustment]:
        """Seluruh riwayat adjust satu run, terbaru dulu."""
        result = await self._session.execute(
            select(CapacityAdjustment)
            .where(CapacityAdjustment.run_id == run_id)
            .order_by(CapacityAdjustment.created_at.desc())
        )
        return list(result.scalars().all())
