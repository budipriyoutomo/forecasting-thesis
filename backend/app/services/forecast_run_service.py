"""
ForecastRunService (v3.0) — orkestrasi satu forecast run untuk BANYAK PRODUK jadi.

Alur (produk-only, docs/ARCHITECTURE.md §6):
  1. Ambil histori demand tiap produk dari demand_history (seri `actual`).
  2. forecast_service (SATU-SATUNYA entry point engine) → forecast_results(product_id).

Hasil run berhenti di level produk — tidak ada turunan ke BOM/material di sini.

Kegagalan satu produk dicatat per-baris & TIDAK menggagalkan run (AGENTS.md §5).
Metode manual tak dikenal ditolak di awal (400) sebelum run dibuat (§6.6).

Metode aktif & opsi engine dibaca SEKALI per run dari master data Pengaturan Forecast
(`settings`, Fase 11.2a). Fase 11.15: mode otomatis tidak memilih pemenang —
`forecast_runs.ranking_metric` hanya riwayat run lama (run baru NULL).
Variabel eksternal aktif (`external`, Fase 11.2b) disusun per produk → `options.exog`.
"""
from dataclasses import replace
from datetime import datetime, timezone

import pandas as pd

from app.models.forecast_result import ForecastResult
from app.models.forecast_run import ForecastRun
from app.services.forecasting import forecast_service, registry
from app.services.forecasting.types import EngineOptions
from app.utils.exceptions import (
    ForbiddenRoleError,
    ForecastRunNotFoundError,
    ProductNotFoundError,
    UnsupportedForecastMethodError,
)


def forecast_summary(points) -> dict | None:
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
    def __init__(self, forecast_repo, products, demand, settings=None, external=None):
        self._repo = forecast_repo
        self._products = products
        self._demand = demand
        self._settings = settings  # ForecastSettingsService; None → seluruh registry
        self._external = external  # ExternalVariableService; None → tanpa variabel eksternal

    async def create_run(
        self,
        user_id: str,
        product_ids: list[str],
        horizon: int,
        horizon_unit: str = "days",
        method: str | None = None,
        now: datetime | None = None,
    ):
        now = now or datetime.now(timezone.utc)

        # Metode aktif dari master data, dibaca sekali per run (Fase 11.2a).
        enabled = await self._settings.enabled_methods() if self._settings else registry.get_enabled_methods()
        options = await self._settings.engine_options() if self._settings else EngineOptions()

        # Validasi metode manual di AWAL — tolak seluruh request kalau tak dikenal (§6.6).
        if method is not None and method not in enabled:
            raise UnsupportedForecastMethodError(
                f"Metode '{method}' tidak dikenal atau tidak aktif."
            )

        # Semua product_id wajib ada di master data (404 kalau ada yang tidak).
        products = []
        for pid in product_ids:
            product = await self._products.get_by_id(pid)
            if product is None:
                raise ProductNotFoundError(f"Produk '{pid}' tidak ditemukan.")
            products.append(product)

        run = ForecastRun(
            user_id=user_id,
            horizon=horizon,
            horizon_unit=horizon_unit,
            status="PROCESSING",
        )
        await self._repo.add_run(run)

        results = []
        for product in products:
            record = await self._forecast_one(product, horizon, method, enabled, options)
            results.append(
                ForecastResult(
                    run_id=run.id,
                    product_id=product.id,
                    status=record.status,
                    method_used=record.method_used,
                    selection_mode=record.selection_mode,
                    candidates_evaluated=record.candidates_evaluated,
                    mad=record.mad,
                    mfe=record.mfe,
                    mse=record.mse,
                    mape=record.mape,
                    mase=record.mase,
                    explanation=record.explanation,
                    forecast_data=[p.__dict__ for p in record.forecast] if record.forecast else None,
                    metrics=forecast_summary(record.forecast),
                    feature_importance=record.feature_importance,
                    hyperparameters=record.hyperparameters,
                )
            )
        if results:
            await self._repo.add_results(results)

        run.status = "COMPLETED"
        run.completed_at = now
        await self._repo.save_run(run)
        return run, results

    async def _forecast_one(
        self,
        product,
        horizon: int,
        method: str | None,
        enabled: set[str],
        options: EngineOptions,
    ):
        rows = await self._demand.list_for_product(str(product.id), product.code)
        # Kolom eksplisit supaya df punya skema saat rows kosong (INSUFFICIENT_DATA,
        # bukan crash). `actual` = target/label ML → dipetakan ke kolom `quantity`.
        df = pd.DataFrame(
            [{"date": str(r.period), "quantity": float(r.actual)} for r in rows],
            columns=["date", "quantity"],
        )
        return forecast_service.run_forecast_for_product(
            df,
            horizon,
            requested_method=method,
            enabled_methods=enabled,
            options=replace(options, exog=await self._external.exog_for_product(product.id))
            if self._external
            else options,
        )

    async def get_run(self, user_id: str, run_id: str):
        run = await self._require_run(user_id, run_id)
        results = await self._repo.list_results(run_id)
        return run, results

    async def get_results_for_product(self, product_id: str):
        return await self._repo.list_results_for_product(product_id)

    async def _require_run(self, user_id: str, run_id: str):
        run = await self._repo.get_run(run_id)
        if run is None:
            raise ForecastRunNotFoundError("Forecast run tidak ditemukan.")
        if str(run.user_id) != str(user_id):
            raise ForbiddenRoleError("Anda tidak berhak mengakses run ini.")
        return run
