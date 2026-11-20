"""Repository stok ERP (Fase 11.5). Repository kedatangan manual dihapus 20 Nov 2026."""
from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import StockSnapshot


class SqlStockSnapshotRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def upsert(self, rows: list[StockSnapshot]) -> int:
        for r in rows:
            await self._session.execute(
                delete(StockSnapshot).where(
                    StockSnapshot.material_id == r.material_id, StockSnapshot.snapshot_date == r.snapshot_date
                )
            )
        self._session.add_all(rows)
        await self._session.flush()
        return len(rows)

    async def list(self, material_id=None, snapshot_date=None) -> list[StockSnapshot]:
        stmt = select(StockSnapshot)
        if material_id is not None:
            stmt = stmt.where(StockSnapshot.material_id == material_id)
        if snapshot_date is not None:
            stmt = stmt.where(StockSnapshot.snapshot_date == snapshot_date)
        result = await self._session.execute(stmt.order_by(StockSnapshot.snapshot_date))
        return list(result.scalars().all())
