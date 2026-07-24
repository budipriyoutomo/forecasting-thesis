"""
ForecastRunService — orkestrasi satu forecast run untuk BANYAK material (Fase 4).

Ambil histori tiap material dari consumption_history → jalankan Auto Model
Selection / manual (lewat forecast_service, SATU-SATUNYA entry point engine) →
persist forecast_results. Kegagalan satu material dicatat per-baris dan TIDAK
menggagalkan run (AGENTS.md §5). Metode manual yang tidak dikenal ditolak di
awal (400) sebelum run dibuat (§6.8).
"""
from datetime import datetime, timezone

import pandas as pd

from app.models.forecast_result import ForecastResult
from app.models.forecast_run import ForecastRun
from app.services.forecasting import forecast_service, registry
from app.utils.exceptions import (
    ForbiddenRoleError,
    ForecastRunNotFoundError,
    MaterialNotFoundError,
    UnsupportedForecastMethodError,
)


def _metrics(points) -> dict | None:
    if not points:
        return None
    values = [p.value for p in points]
    first = values[0]
    trend = values[-1] - first
    direction = "up" if trend > 0 else "down" if trend < 0 else "flat"
    return {
        "avg_forecast": sum(values) / len(values),
        "trend_direction": direction,
        "trend_pct": (trend / first * 100) if first else 0.0,
    }


class ForecastRunService:
    def __init__(self, forecast_repo, materials, consumptions):
        self._repo = forecast_repo
        self._materials = materials
        self._consumptions = consumptions

    async def create_run(
        self,
        user_id: str,
        material_ids: list[str],
        horizon: int,
        horizon_unit: str = "days",
        method: str | None = None,
        now: datetime | None = None,
    ):
        now = now or datetime.now(timezone.utc)

        # Validasi metode manual di AWAL — tolak seluruh request kalau tak dikenal (§6.8),
        # bukan diam-diam per material.
        if method is not None and method not in registry.get_enabled_methods():
            raise UnsupportedForecastMethodError(
                f"Metode '{method}' tidak dikenal atau tidak aktif."
            )

        # Semua material_id wajib ada di master data (404 kalau ada yang tidak).
        materials = []
        for mid in material_ids:
            material = await self._materials.get_by_id(mid)
            if material is None:
                raise MaterialNotFoundError(f"Material '{mid}' tidak ditemukan.")
            materials.append(material)

        run = ForecastRun(
            user_id=user_id, horizon=horizon, horizon_unit=horizon_unit, status="PROCESSING"
        )
        await self._repo.add_run(run)

        results = []
        for material in materials:
            record = await self._forecast_one(material, horizon, method)
            results.append(
                ForecastResult(
                    run_id=run.id,
                    material_id=material.id,
                    status=record.status,
                    data_profile={"demand_class": record.demand_class} if record.demand_class else None,
                    method_used=record.method_used,
                    selection_mode=record.selection_mode,
                    mase=record.mase,
                    explanation=record.explanation,
                    forecast_data=[p.__dict__ for p in record.forecast] if record.forecast else None,
                    metrics=_metrics(record.forecast),
                )
            )
        if results:
            await self._repo.add_results(results)

        run.status = "COMPLETED"
        run.completed_at = now
        await self._repo.save_run(run)
        return run, results

    async def _forecast_one(self, material, horizon: int, method: str | None):
        rows = await self._consumptions.list_for_material(str(material.id), material.code)
        # columns eksplisit supaya df tetap punya skema saat rows kosong (material
        # tanpa histori) — downstream cukup mendeteksi INSUFFICIENT_DATA, bukan crash.
        df = pd.DataFrame(
            [{"date": str(r.date), "quantity": float(r.quantity)} for r in rows],
            columns=["date", "quantity"],
        )
        return forecast_service.run_forecast_for_material(df, horizon, requested_method=method)

    async def get_run(self, user_id: str, run_id: str):
        run = await self._repo.get_run(run_id)
        if run is None:
            raise ForecastRunNotFoundError("Forecast run tidak ditemukan.")
        if str(run.user_id) != str(user_id):
            raise ForbiddenRoleError("Anda tidak berhak mengakses run ini.")
        results = await self._repo.list_results(run_id)
        return run, results

    async def get_results_for_material(self, material_id: str):
        return await self._repo.list_results_for_material(material_id)
