"""Repository pemakaian aktual material (Fase 11.1) — upsert per (material, produk, periode)."""
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.material_usage import MaterialUsage


class SqlMaterialUsageRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def upsert(self, rows: list[MaterialUsage]) -> int:
        for r in rows:
            product_cond = (
                MaterialUsage.product_id.is_(None) if r.product_id is None else MaterialUsage.product_id == r.product_id
            )
            await self._session.execute(
                delete(MaterialUsage).where(
                    MaterialUsage.material_id == r.material_id, MaterialUsage.period == r.period, product_cond
                )
            )
        self._session.add_all(rows)
        await self._session.flush()
        return len(rows)

    async def list(self, material_id=None) -> list[MaterialUsage]:
        stmt = select(MaterialUsage)
        if material_id is not None:
            stmt = stmt.where(MaterialUsage.material_id == material_id)
        result = await self._session.execute(stmt.order_by(MaterialUsage.period))
        return list(result.scalars().all())

    async def totals_by_material(self, material_ids=None) -> dict[str, tuple[float, float]]:
        stmt = select(
            MaterialUsage.material_id, func.sum(MaterialUsage.actual_usage), func.sum(MaterialUsage.standard_usage)
        ).group_by(MaterialUsage.material_id)
        if material_ids is not None:
            stmt = stmt.where(MaterialUsage.material_id.in_(list(material_ids)))
        result = await self._session.execute(stmt)
        return {str(mid): (float(a or 0), float(s or 0)) for mid, a, s in result.all()}
