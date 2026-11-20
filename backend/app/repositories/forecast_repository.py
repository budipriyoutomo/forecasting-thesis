"""
ForecastRun & ForecastResult repository — docs/ARCHITECTURE.md §4.
"""
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.forecast_result import ForecastResult
from app.models.forecast_run import ForecastRun
from app.models.user import User


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

    async def get_latest_run(self) -> ForecastRun | None:
        """Run terbaru organisasi (dashboard) — CR v3.5 §3.4 Opsi A, tanpa filter pemilik."""
        result = await self._session.execute(
            select(ForecastRun).order_by(desc(ForecastRun.created_at)).limit(1)
        )
        return result.scalar_one_or_none()

    async def list_runs(self, limit: int = 50) -> list[tuple[ForecastRun, str | None]]:
        """Semua run, terbaru dulu, beserta label pembuatnya (nama, fallback email).

        Dipakai pemilih run halaman Kedatangan Material. CR v3.5 §3.4 Opsi A: run
        terlihat semua role (single-tenant), jadi tidak ada filter pemilik.
        """
        result = await self._session.execute(
            select(ForecastRun, User.name, User.email)
            .outerjoin(User, User.id == ForecastRun.user_id)
            .order_by(desc(ForecastRun.created_at))
            .limit(limit)
        )
        return [(run, name or email) for run, name, email in result.all()]

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

    async def list_results_for_product(self, product_id: str) -> list[ForecastResult]:
        result = await self._session.execute(
            select(ForecastResult)
            .where(ForecastResult.product_id == product_id)
            .order_by(ForecastResult.created_at.desc())
        )
        return list(result.scalars().all())
