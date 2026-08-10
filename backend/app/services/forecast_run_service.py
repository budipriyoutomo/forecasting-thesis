"""
ForecastRunService (v3.0) — orkestrasi satu forecast run untuk BANYAK PRODUK jadi.

Alur (produk-only, docs/ARCHITECTURE.md §6):
  1. Ambil histori demand tiap produk dari demand_history (seri `actual`).
  2. forecast_service (SATU-SATUNYA entry point engine) → forecast_results(product_id).
  3. Breakdown BOM: forecast produk × qty_per_unit → material_requirements per material.

Kegagalan satu produk dicatat per-baris & TIDAK menggagalkan run (AGENTS.md §5).
Metode manual tak dikenal ditolak di awal (400) sebelum run dibuat (§6.6).
"""
from datetime import datetime, timezone

import pandas as pd

from app.models.forecast_result import ForecastResult
from app.models.forecast_run import ForecastRun
from app.models.material_requirement import MaterialRequirement
from app.services.bom_service import BomLine, breakdown_requirements
from app.services.forecasting import forecast_service, registry
from app.utils.exceptions import (
    ForbiddenRoleError,
    ForecastRunNotFoundError,
    ProductNotFoundError,
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
    def __init__(self, forecast_repo, products, demand, boms=None, requirements=None):
        self._repo = forecast_repo
        self._products = products
        self._demand = demand
        self._boms = boms
        self._requirements = requirements

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

        # Validasi metode manual di AWAL — tolak seluruh request kalau tak dikenal (§6.6).
        if method is not None and method not in registry.get_enabled_methods():
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
            user_id=user_id, horizon=horizon, horizon_unit=horizon_unit, status="PROCESSING"
        )
        await self._repo.add_run(run)

        results = []
        product_forecast_qty: dict[str, float] = {}
        for product in products:
            record = await self._forecast_one(product, horizon, method)
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
                    metrics=_metrics(record.forecast),
                )
            )
            if record.status == "COMPLETED" and record.forecast:
                product_forecast_qty[str(product.id)] = sum(p.value for p in record.forecast)

        if results:
            await self._repo.add_results(results)

        await self._build_requirements(run, product_forecast_qty)

        run.status = "COMPLETED"
        run.completed_at = now
        await self._repo.save_run(run)
        return run, results

    async def _forecast_one(self, product, horizon: int, method: str | None):
        rows = await self._demand.list_for_product(str(product.id), product.code)
        # Kolom eksplisit supaya df punya skema saat rows kosong (INSUFFICIENT_DATA,
        # bukan crash). `actual` = target/label ML → dipetakan ke kolom `quantity`.
        df = pd.DataFrame(
            [{"date": str(r.period), "quantity": float(r.actual)} for r in rows],
            columns=["date", "quantity"],
        )
        return forecast_service.run_forecast_for_product(df, horizon, requested_method=method)

    async def _build_requirements(self, run, product_forecast_qty: dict[str, float]) -> None:
        """Breakdown BOM → material_requirements per run (Fase 5). No-op bila repo/BOM
        tak diinjeksi atau tak ada forecast produk yang berhasil."""
        if self._boms is None or self._requirements is None or not product_forecast_qty:
            return
        bom_lines: list[BomLine] = []
        for pid in product_forecast_qty:
            for bom in await self._boms.list(pid):
                bom_lines.append(BomLine(str(bom.product_id), str(bom.material_id), float(bom.qty_per_unit)))
        requirements = breakdown_requirements(product_forecast_qty, bom_lines)
        rows = [
            MaterialRequirement(run_id=run.id, material_id=material_id, forecast_qty=qty)
            for material_id, qty in requirements.items()
        ]
        await self._requirements.replace_for_run(str(run.id), rows)

    async def get_run(self, user_id: str, run_id: str):
        run = await self._require_run(user_id, run_id)
        results = await self._repo.list_results(run_id)
        return run, results

    async def get_results_for_product(self, product_id: str):
        return await self._repo.list_results_for_product(product_id)

    async def list_requirements(self, user_id: str, run_id: str):
        """Kebutuhan material hasil breakdown BOM untuk satu run (Fase 5, dibaca Fase 9).

        Repo opsional — pola sama dengan `_build_requirements`: tanpa repo, run
        tetap valid, hanya tak punya requirement untuk ditampilkan.
        """
        await self._require_run(user_id, run_id)
        if self._requirements is None:
            return []
        return await self._requirements.list_by_run(run_id)

    async def _require_run(self, user_id: str, run_id: str):
        run = await self._repo.get_run(run_id)
        if run is None:
            raise ForecastRunNotFoundError("Forecast run tidak ditemukan.")
        if str(run.user_id) != str(user_id):
            raise ForbiddenRoleError("Anda tidak berhak mengakses run ini.")
        return run
