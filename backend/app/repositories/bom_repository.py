"""
BomRepository — akses tabel `boms` (docs/ARCHITECTURE.md §4).
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bom import Bom


class SqlBomRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def list(self, product_id: str | None = None) -> list[Bom]:
        stmt = select(Bom)
        if product_id is not None:
            stmt = stmt.where(Bom.product_id == product_id)
        result = await self._session.execute(stmt.order_by(Bom.created_at))
        return list(result.scalars().all())

    async def get_by_id(self, bom_id: str) -> Bom | None:
        return await self._session.get(Bom, bom_id)

    async def add(self, bom: Bom) -> Bom:
        self._session.add(bom)
        await self._session.flush()
        await self._session.refresh(bom)
        return bom

    async def save(self, bom: Bom) -> Bom:
        await self._session.flush()
        await self._session.refresh(bom)
        return bom

    async def delete(self, bom: Bom) -> None:
        await self._session.delete(bom)
        await self._session.flush()
