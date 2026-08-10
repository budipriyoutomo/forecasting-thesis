"""
MaterialRepository — akses tabel `materials` (docs/ARCHITECTURE.md §4).
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.material import Material


class SqlMaterialRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def list(self) -> list[Material]:
        result = await self._session.execute(select(Material).order_by(Material.code))
        return list(result.scalars().all())

    async def get_by_id(self, material_id: str) -> Material | None:
        return await self._session.get(Material, material_id)

    async def get_by_code(self, code: str) -> Material | None:
        result = await self._session.execute(select(Material).where(Material.code == code))
        return result.scalar_one_or_none()

    async def map_codes_to_ids(self, codes: set[str]) -> dict[str, str]:
        """Peta code → id untuk kode yang terdaftar (dipakai saat import master data)."""
        if not codes:
            return {}
        result = await self._session.execute(
            select(Material.code, Material.id).where(Material.code.in_(codes))
        )
        return {code: str(mid) for code, mid in result.all()}

    async def add(self, material: Material) -> Material:
        self._session.add(material)
        await self._session.flush()
        await self._session.refresh(material)
        return material

    async def save(self, material: Material) -> Material:
        await self._session.flush()
        await self._session.refresh(material)
        return material

    async def delete(self, material: Material) -> None:
        await self._session.delete(material)
        await self._session.flush()
