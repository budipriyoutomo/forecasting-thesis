"""
Inventory metrics repository (v3.0 Fase 7) — docs/ARCHITECTURE.md §4.

Replace-per-run (idempotent): hitung ulang metrik satu run selalu mengganti
baris lama run tersebut, bukan menumpuk (pola sama warehouse_validations).
"""
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory_metrics import InventoryMetric


class SqlInventoryMetricsRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def replace_for_run(self, run_id: str, rows: list[InventoryMetric]) -> list[InventoryMetric]:
        await self._session.execute(
            delete(InventoryMetric).where(InventoryMetric.run_id == run_id)
        )
        for row in rows:
            self._session.add(row)
        await self._session.flush()
        for row in rows:
            await self._session.refresh(row)
        return rows

    async def list_by_run(self, run_id: str) -> list[InventoryMetric]:
        result = await self._session.execute(
            select(InventoryMetric).where(InventoryMetric.run_id == run_id)
        )
        return list(result.scalars().all())
