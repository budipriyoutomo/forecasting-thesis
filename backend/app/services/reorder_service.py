"""
ReorderService — safety stock & reorder point (Fase 5), docs/ARCHITECTURE.md §4.

`compute_reorder` adalah FUNGSI MURNI (mudah diverifikasi manual, AGENTS.md §3):

  SS  = manual_safety_stock jika diisi, else Z · σ_harian · sqrt(lead_time)
  ROP = μ_harian · lead_time + SS
  S   = order-up-to = ROP + μ_harian · lead_time
  current ≤ ROP      → urgent   (qty = max(MOQ, ceil(S − current)))
  ROP < current ≤ S  → safe     (qty = 0)
  current > S        → overstock (qty = 0)

Orkestrasi (`ReorderService`) menghitung μ/σ dari deret kebutuhan material
hasil breakdown BOM atas forecast produk, dan mengambil lead_time/MOQ/manual SS
dari master data material.
"""
import math
from dataclasses import dataclass
from decimal import Decimal

import numpy as np

from app.config import get_settings
from app.models.reorder_recommendation import ReorderRecommendation
from app.services.bom_service import BomLine, breakdown_requirements_series
from app.utils.exceptions import ForbiddenRoleError, ForecastRunNotFoundError


def _dec(value) -> Decimal:
    return Decimal(str(round(float(value), 4)))


@dataclass
class ReorderComputation:
    safety_stock: Decimal
    reorder_point: Decimal
    recommended_order_qty: Decimal
    status: str


@dataclass
class EOQResult:
    n: int  # jumlah pemesanan optimal pada horizon
    eoq_qty: Decimal  # ukuran pesanan ekonomis (belum dibulatkan ke MOQ)
    total_cost: Decimal  # TC = n·S + Σ(Iₜ·H)


def _split_cycles(n_periods: int, n_orders: int) -> list[tuple[int, int]]:
    """Bagi `n_periods` jadi `n_orders` siklus kontigu sebanyak-mungkin merata."""
    base, extra = divmod(n_periods, n_orders)
    cycles, start = [], 0
    for i in range(n_orders):
        length = base + (1 if i < extra else 0)
        if length == 0:
            continue
        cycles.append((start, start + length))
        start += length
    return cycles


def compute_eoq(demands: list[float], ordering_cost: float, holding_cost: float) -> EOQResult:
    """
    EOQ dinamis (Bab III thesis): TC = n·S + Σ(Iₜ·H), Iₜ = persediaan akhir periode t.
    Simulasikan tiap kandidat jumlah pemesanan n (1..T): tiap order menutup demand
    siklusnya, hitung total biaya, pilih n dengan TC minimum. Fungsi murni,
    diverifikasi manual di test (AGENTS.md §3).
    """
    demands = [float(d) for d in demands]
    horizon = len(demands)
    total = sum(demands)
    if horizon == 0 or total <= 0:
        return EOQResult(n=1, eoq_qty=_dec(0), total_cost=_dec(ordering_cost))

    best_n, best_cost = 1, None
    for n in range(1, horizon + 1):
        inventory, holding = 0.0, 0.0
        for start, end in _split_cycles(horizon, n):
            inventory += sum(demands[start:end])  # order menutup demand siklus ini
            for t in range(start, end):
                inventory -= demands[t]
                holding += inventory * holding_cost  # biaya simpan persediaan akhir periode
        total_cost = n * ordering_cost + holding
        if best_cost is None or total_cost < best_cost:
            best_n, best_cost = n, total_cost

    return EOQResult(n=best_n, eoq_qty=_dec(total / best_n), total_cost=_dec(best_cost))


def round_to_moq(qty: float, moq: float) -> Decimal:
    """Bulatkan qty ke kelipatan MOQ ke atas (MOQ sebagai batas bawah)."""
    qty, moq = float(qty), float(moq)
    if moq <= 0:
        return _dec(qty)
    return _dec(math.ceil(round(qty / moq, 6)) * moq)


def compute_tic(ordering_cost_total: float, holding_cost_total: float) -> Decimal:
    """Total Inventory Cost = Ordering Cost + Holding Cost."""
    return _dec(float(ordering_cost_total) + float(holding_cost_total))


def compute_savings_pct(tic_actual: float, tic_proposed: float) -> Decimal:
    """% penghematan = (TIC aktual − TIC usulan) / TIC aktual × 100."""
    tic_actual = float(tic_actual)
    if tic_actual == 0:
        return _dec(0)
    return _dec((tic_actual - float(tic_proposed)) / tic_actual * 100)


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



class ReorderService:
    """
    v3.0: reorder dihitung PER MATERIAL dari hasil breakdown BOM atas forecast
    produk jadi (bukan lagi dari consumption_history material). Deret kebutuhan
    material per periode = Σ_produk (forecast_produk[t] × qty_per_unit) → μ/σ untuk
    safety stock, dan sebagai demand EOQ.
    """

    def __init__(self, reorder_repo, forecast_repo, boms, materials):
        self._repo = reorder_repo
        self._forecast = forecast_repo
        self._boms = boms
        self._materials = materials

    async def generate_for_run(self, user_id: str, run_id: str, current_stock: dict | None = None):
        run = await self._require_run(user_id, run_id)
        current_stock = current_stock or {}
        settings = get_settings()
        z = settings.SERVICE_LEVEL_Z

        # Deret forecast per produk (hanya yang COMPLETED & punya data).
        product_series: dict[str, list[float]] = {}
        for result in await self._forecast.list_results(run_id):
            if result.status != "COMPLETED":
                continue
            fdata = getattr(result, "forecast_data", None) or []
            if fdata:
                product_series[str(result.product_id)] = [float(p.get("value", 0)) for p in fdata]

        # Breakdown BOM → deret kebutuhan per material.
        bom_lines: list[BomLine] = []
        for pid in product_series:
            for bom in await self._boms.list(pid):
                bom_lines.append(BomLine(str(bom.product_id), str(bom.material_id), float(bom.qty_per_unit)))
        material_series = breakdown_requirements_series(product_series, bom_lines)

        recommendations = []
        for material_id, series in material_series.items():
            material = await self._materials.get_by_id(material_id)
            if material is None:
                continue
            arr = np.asarray(series, dtype=float)
            mu = float(np.mean(arr)) if len(arr) else 0.0
            sigma = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
            comp = compute_reorder(
                mu=mu,
                sigma=sigma,
                lead_time_days=material.lead_time_days,
                moq=float(material.moq),
                z=z,
                manual_ss=float(material.manual_safety_stock)
                if material.manual_safety_stock is not None
                else None,
                current_stock=float(current_stock.get(material_id, 0)),
            )

            eoq = compute_eoq(series, settings.DEFAULT_ORDERING_COST, settings.DEFAULT_HOLDING_COST_RATE)
            eoq_qty = round_to_moq(float(eoq.eoq_qty), float(material.moq))
            ordering_total = eoq.n * settings.DEFAULT_ORDERING_COST
            holding_total = float(eoq.total_cost) - ordering_total

            recommendations.append(
                ReorderRecommendation(
                    run_id=run.id,
                    material_id=material.id,
                    safety_stock=comp.safety_stock,
                    reorder_point=comp.reorder_point,
                    recommended_order_qty=comp.recommended_order_qty,
                    status=comp.status,
                    eoq_qty=eoq_qty,
                    ordering_cost=_dec(ordering_total),
                    holding_cost=_dec(holding_total),
                    total_inventory_cost=compute_tic(ordering_total, holding_total),
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
