"""
ReorderService — safety stock & reorder point (Fase 5), docs/ARCHITECTURE.md §4.

`compute_reorder` adalah FUNGSI MURNI (mudah diverifikasi manual, AGENTS.md §3):

  SS  = manual_safety_stock jika diisi, else Z · σ_harian · sqrt(lead_time)
  ROP = μ_harian · lead_time + SS
  S   = order-up-to = ROP + μ_harian · lead_time
  current ≤ ROP      → urgent   (qty = max(MOQ, ceil(S − current)))
  ROP < current ≤ S  → safe     (qty = 0)
  current > S        → overstock (qty = 0)

Orkestrasi (`ReorderService`) menghitung μ/σ dari consumption_history dan
mengambil lead_time/MOQ/manual SS dari master data material.
"""
import math
from dataclasses import dataclass
from decimal import Decimal

import numpy as np
import pandas as pd

from app.config import get_settings
from app.models.reorder_recommendation import ReorderRecommendation
from app.services.forecasting.preprocessing import to_daily_series
from app.utils.exceptions import ForbiddenRoleError, ForecastRunNotFoundError


def _dec(value) -> Decimal:
    return Decimal(str(round(float(value), 4)))


@dataclass
class ReorderComputation:
    safety_stock: Decimal
    reorder_point: Decimal
    recommended_order_qty: Decimal
    status: str


def compute_reorder(
    mu: float,
    sigma: float,
    lead_time_days: float,
    moq: float,
    z: float,
    manual_ss: float | None,
    current_stock: float,
) -> ReorderComputation:
    mu, sigma = float(mu), float(sigma)
    lt, moq, current = float(lead_time_days), float(moq), float(current_stock)

    ss = float(manual_ss) if manual_ss is not None else z * sigma * math.sqrt(lt)
    demand_over_lt = mu * lt
    rop = demand_over_lt + ss
    order_up_to = rop + demand_over_lt

    if current <= rop:
        status = "urgent"
        # round sebelum ceil supaya galat float (mis. 40.0000000001) tidak jadi 41
        need = round(order_up_to - current, 6)
        qty = max(moq, float(math.ceil(need)))
    elif current <= order_up_to:
        status, qty = "safe", 0.0
    else:
        status, qty = "overstock", 0.0

    return ReorderComputation(_dec(ss), _dec(rop), _dec(qty), status)


def demand_stats(rows) -> tuple[float, float]:
    """μ dan σ konsumsi harian dari consumption_history (series harian, hari kosong = 0)."""
    if not rows:
        return 0.0, 0.0
    df = pd.DataFrame(
        [{"date": str(r.date), "quantity": float(r.quantity)} for r in rows],
        columns=["date", "quantity"],
    )
    series = to_daily_series(df)
    values = series.to_numpy(dtype=float)
    mu = float(np.mean(values))
    sigma = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
    return mu, sigma


class ReorderService:
    def __init__(self, reorder_repo, forecast_repo, materials, consumptions):
        self._repo = reorder_repo
        self._forecast = forecast_repo
        self._materials = materials
        self._consumptions = consumptions

    async def generate_for_run(self, user_id: str, run_id: str, current_stock: dict | None = None):
        run = await self._require_run(user_id, run_id)
        current_stock = current_stock or {}
        z = get_settings().SERVICE_LEVEL_Z

        results = await self._forecast.list_results(run_id)
        recommendations = []
        for result in results:
            if result.status != "COMPLETED":
                continue  # material yang forecast-nya gagal tidak diberi rekomendasi
            material = await self._materials.get_by_id(str(result.material_id))
            if material is None:
                continue
            rows = await self._consumptions.list_for_material(str(material.id), material.code)
            mu, sigma = demand_stats(rows)
            comp = compute_reorder(
                mu=mu,
                sigma=sigma,
                lead_time_days=material.lead_time_days,
                moq=float(material.moq),
                z=z,
                manual_ss=float(material.manual_safety_stock)
                if material.manual_safety_stock is not None
                else None,
                current_stock=float(current_stock.get(str(material.id), 0)),
            )
            recommendations.append(
                ReorderRecommendation(
                    run_id=run.id,
                    material_id=material.id,
                    safety_stock=comp.safety_stock,
                    reorder_point=comp.reorder_point,
                    recommended_order_qty=comp.recommended_order_qty,
                    status=comp.status,
                )
            )

        await self._repo.replace_for_run(str(run_id), recommendations)
        return recommendations

    async def list_for_run(self, user_id: str, run_id: str, status: str | None = None):
        await self._require_run(user_id, run_id)
        recs = await self._repo.list_by_run(run_id)
        if status:
            recs = [r for r in recs if r.status == status]
        return recs

    async def _require_run(self, user_id: str, run_id: str):
        run = await self._forecast.get_run(run_id)
        if run is None:
            raise ForecastRunNotFoundError("Forecast run tidak ditemukan.")
        if str(run.user_id) != str(user_id):
            raise ForbiddenRoleError("Anda tidak berhak mengakses run ini.")
        return run
