"""
ForecastRun & ForecastResult repository — docs/ARCHITECTURE.md §4.
"""
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.forecast_result import ForecastResult
from app.models.forecast_run import ForecastRun


class SqlForecastRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add_run(self, run: ForecastRun) -> ForecastRun:
        self._session.add(run)
        await self._session.flush()
        await self._session.refresh(run)
        return run

    async def get_run(self, run_id: str) -> ForecastRun | None:
        return await self._session.get(ForecastRun, run_id)

    async def get_result(self, result_id: str) -> ForecastResult | None:
        return await self._session.get(ForecastResult, result_id)

    async def get_latest_run_for_user(self, user_id: str) -> ForecastRun | None:
        result = await self._session.execute(
            select(ForecastRun)
            .where(ForecastRun.user_id == user_id)
            .order_by(desc(ForecastRun.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def save_run(self, run: ForecastRun) -> ForecastRun:
        await self._session.flush()
        return run

    async def add_results(self, results: list[ForecastResult]) -> int:
        self._session.add_all(results)
        await self._session.flush()
        return len(results)

    async def list_results(self, run_id: str) -> list[ForecastResult]:
        result = await self._session.execute(
            select(ForecastResult).where(ForecastResult.run_id == run_id)
        )
        return list(result.scalars().all())

    async def list_results_for_material(self, material_id: str) -> list[ForecastResult]:
        result = await self._session.execute(
            select(ForecastResult)
            .where(ForecastResult.material_id == material_id)
            .order_by(ForecastResult.created_at.desc())
        )
        return list(result.scalars().all())
