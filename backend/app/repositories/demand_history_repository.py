"""
DemandHistoryRepository (v3.0) — akses tabel `demand_history` (docs/ARCHITECTURE.md §4).
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.demand_history import DemandHistory


class SqlDemandHistoryRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def bulk_add(self, rows: list[DemandHistory]) -> int:
        self._session.add_all(rows)
        await self._session.flush()
        return len(rows)

    async def list_for_product(self, product_id: str, product_code: str) -> list[DemandHistory]:
        """Histori demand satu produk — cocokkan lewat id ATAU code (id bisa null,
        pola RECONCILIATION #14). Terurut per periode."""
        result = await self._session.execute(
            select(DemandHistory)
            .where(
                (DemandHistory.product_id == product_id)
                | (DemandHistory.product_code == product_code)
            )
            .order_by(DemandHistory.period)
        )
        return list(result.scalars().all())
