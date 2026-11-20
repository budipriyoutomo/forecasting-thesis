"""
DemandHistoryRepository (v3.0) — akses tabel `demand_history` (docs/ARCHITECTURE.md §4).
"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.demand_history import DemandHistory


class SqlDemandHistoryRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def bulk_add(self, rows: list[DemandHistory]) -> int:
        self._session.add_all(rows)
        await self._session.flush()
        return len(rows)

    async def period_range(self):
        """(periode demand pertama, terakhir) lintas produk; (None, None) bila kosong."""
        result = await self._session.execute(select(func.min(DemandHistory.period), func.max(DemandHistory.period)))
        first, last = result.one()
        return first, last

    async def list_unnormalized(self) -> list[DemandHistory]:
        """Baris dengan periode bukan tanggal 1 (data sebelum CR v3.4 §4.1)."""
        result = await self._session.execute(
            select(DemandHistory).where(func.extract("day", DemandHistory.period) != 1).order_by(DemandHistory.period)
        )
        return list(result.scalars().all())

    async def normalized_keys(self) -> set[tuple]:
        """(upload_session_id, product_code, period) untuk baris yang sudah tanggal 1."""
        result = await self._session.execute(
            select(DemandHistory.upload_session_id, DemandHistory.product_code, DemandHistory.period).where(
                func.extract("day", DemandHistory.period) == 1
            )
        )
        return {(str(sid), code, period) for sid, code, period in result.all()}

    async def flush(self) -> None:
        await self._session.flush()

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
