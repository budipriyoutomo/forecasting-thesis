"""
MaterialRequirementRepository (v3.0) — akses tabel `material_requirements`
(docs/ARCHITECTURE.md §4). Dipakai saat breakdown BOM per run dipersist.
"""
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.material_requirement import MaterialRequirement


class SqlMaterialRequirementRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def replace_for_run(self, run_id: str, requirements: list[MaterialRequirement]) -> int:
        """Regenerasi: hapus requirement lama untuk run ini, ganti dengan yang baru."""
        await self._session.execute(
            delete(MaterialRequirement).where(MaterialRequirement.run_id == run_id)
        )
        if requirements:
            self._session.add_all(requirements)
        await self._session.flush()
        return len(requirements)

    async def list_by_run(self, run_id: str) -> list[MaterialRequirement]:
        result = await self._session.execute(
            select(MaterialRequirement).where(MaterialRequirement.run_id == run_id)
        )
        return list(result.scalars().all())

    async def get_requirement(self, req_id: str) -> MaterialRequirement | None:
        return await self._session.get(MaterialRequirement, req_id)
