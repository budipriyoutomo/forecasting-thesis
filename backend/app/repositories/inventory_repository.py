"""Repository stok ERP & kedatangan material (Fase 11.5)."""
from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import MaterialReceipt, StockSnapshot


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


class SqlMaterialReceiptRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def list(self, material_id=None, date_from=None, date_to=None) -> list[MaterialReceipt]:
        stmt = select(MaterialReceipt)
        if material_id is not None:
            stmt = stmt.where(MaterialReceipt.material_id == material_id)
        if date_from is not None:
            stmt = stmt.where(MaterialReceipt.expected_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(MaterialReceipt.expected_date <= date_to)
        result = await self._session.execute(stmt.order_by(MaterialReceipt.expected_date))
        return list(result.scalars().all())

    async def get_by_id(self, receipt_id) -> MaterialReceipt | None:
        return await self._session.get(MaterialReceipt, receipt_id)

    async def add(self, row: MaterialReceipt) -> MaterialReceipt:
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def add_all(self, rows: list[MaterialReceipt]) -> int:
        self._session.add_all(rows)
        await self._session.flush()
        return len(rows)

    async def save(self, row: MaterialReceipt) -> MaterialReceipt:
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def delete(self, row: MaterialReceipt) -> None:
        await self._session.delete(row)
        await self._session.flush()
