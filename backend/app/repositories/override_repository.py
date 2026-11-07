"""
Override repository — append-only audit trail (docs/ARCHITECTURE.md §4).
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.override import Override


class SqlOverrideRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, override: Override) -> Override:
        # APPEND-ONLY: hanya menambah baris baru, tidak pernah update/delete.
        self._session.add(override)
        await self._session.flush()
        await self._session.refresh(override)
        return override

    async def list_by_target(self, target_id: str) -> list[Override]:
        result = await self._session.execute(
            select(Override)
            .where(Override.target_id == target_id)
            .order_by(Override.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_by_context(self, run_id: str, material_id: str | None = None) -> list[Override]:
        """Override dalam satu run (opsional satu material), terbaru dulu — v3.3."""
        stmt = select(Override).where(Override.run_id == run_id)
        if material_id is not None:
            stmt = stmt.where(Override.material_id == material_id)
        result = await self._session.execute(stmt.order_by(Override.created_at.desc()))
        return list(result.scalars().all())

    async def list_recent(self, limit: int = 20) -> list[Override]:
        result = await self._session.execute(
            select(Override).order_by(Override.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())
