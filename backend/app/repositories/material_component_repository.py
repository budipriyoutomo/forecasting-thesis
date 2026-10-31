"""Repository komponen material — BOM level 2+ (Fase 11.3)."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.material_component import MaterialComponent


class SqlMaterialComponentRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def list(self, parent_id=None) -> list[MaterialComponent]:
        stmt = select(MaterialComponent)
        if parent_id is not None:
            stmt = stmt.where(MaterialComponent.parent_material_id == parent_id)
        result = await self._session.execute(stmt.order_by(MaterialComponent.created_at))
        return list(result.scalars().all())

    async def get_by_id(self, component_id) -> MaterialComponent | None:
        return await self._session.get(MaterialComponent, component_id)

    async def add(self, row: MaterialComponent) -> MaterialComponent:
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def delete(self, row: MaterialComponent) -> None:
        await self._session.delete(row)
        await self._session.flush()
