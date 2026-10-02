"""
Repository template biaya (Fase 10, 2 Oktober 2026) — docs/ARCHITECTURE.md §4.
Item dimuat lewat relasi `selectin`; `set_active` memakai UPDATE langsung (bukan flush
per objek) supaya partial unique index `is_active` tidak pernah sempat dilanggar.
"""
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cost_template import CostTemplate


class SqlCostTemplateRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def list(self) -> list[CostTemplate]:
        result = await self._session.execute(select(CostTemplate).order_by(CostTemplate.name))
        return list(result.scalars().all())

    async def get_by_id(self, template_id: str) -> CostTemplate | None:
        return await self._session.get(CostTemplate, template_id)

    async def get_by_name(self, name: str) -> CostTemplate | None:
        result = await self._session.execute(select(CostTemplate).where(CostTemplate.name == name))
        return result.scalar_one_or_none()

    async def get_active(self) -> CostTemplate | None:
        result = await self._session.execute(select(CostTemplate).where(CostTemplate.is_active.is_(True)))
        return result.scalar_one_or_none()

    async def add(self, template: CostTemplate) -> CostTemplate:
        self._session.add(template)
        await self._session.flush()
        await self._session.refresh(template, attribute_names=["items", "created_at", "updated_at"])
        return template

    async def save(self, template: CostTemplate) -> CostTemplate:
        await self._session.flush()
        await self._session.refresh(template, attribute_names=["items", "updated_at"])
        return template

    async def set_active(self, template_id) -> None:
        # Matikan dulu yang lain, baru aktifkan → tak pernah ada dua baris aktif.
        # Nilai literal supaya synchronize_session bisa menyetel objek di session
        # tanpa expire (akses atribut expired di async = MissingGreenlet).
        await self._session.execute(
            update(CostTemplate)
            .where(CostTemplate.is_active.is_(True), CostTemplate.id != template_id)
            .values(is_active=False)
        )
        await self._session.execute(
            update(CostTemplate).where(CostTemplate.id == template_id).values(is_active=True)
        )
        await self._session.flush()

    async def delete(self, template: CostTemplate) -> None:
        await self._session.delete(template)
        await self._session.flush()
