"""Repository proyeksi stok per run (Fase 11.6) — ganti total per run."""
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock_projection import StockProjection


class SqlStockProjectionRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def replace_for_run(self, run_id: str, rows: list[StockProjection]) -> int:
        await self._session.execute(delete(StockProjection).where(StockProjection.run_id == run_id))
        self._session.add_all(rows)
        await self._session.flush()
        return len(rows)

    async def list_by_run(self, run_id: str) -> list[StockProjection]:
        result = await self._session.execute(
            select(StockProjection)
            .where(StockProjection.run_id == run_id)
            .order_by(StockProjection.scenario, StockProjection.material_id, StockProjection.period)
        )
        return list(result.scalars().all())
