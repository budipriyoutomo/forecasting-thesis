"""
ReorderRecommendation repository — docs/ARCHITECTURE.md §4.
"""
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reorder_recommendation import ReorderRecommendation


class SqlReorderRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def replace_for_run(self, run_id: str, recommendations: list[ReorderRecommendation]) -> int:
        """Regenerasi: hapus rekomendasi lama untuk run ini, ganti dengan yang baru."""
        await self._session.execute(
            delete(ReorderRecommendation).where(ReorderRecommendation.run_id == run_id)
        )
        if recommendations:
            self._session.add_all(recommendations)
        await self._session.flush()
        return len(recommendations)

    async def list_by_run(self, run_id: str) -> list[ReorderRecommendation]:
        result = await self._session.execute(
            select(ReorderRecommendation).where(ReorderRecommendation.run_id == run_id)
        )
        return list(result.scalars().all())
