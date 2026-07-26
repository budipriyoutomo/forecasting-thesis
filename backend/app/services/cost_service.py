"""
CostService (v3.0 Fase 7) — ringkasan total biaya persediaan & % penghematan,
docs/ARCHITECTURE.md §6.8 + RECONCILIATION §Fase 7.

Rumus TIC/EOQ/savings TIDAK diduplikasi: `compute_eoq` & `compute_savings_pct`
di-reuse dari `reorder_service.py` (satu sumber kebenaran rumus). Service ini
hanya mengorkestrasi:
  - TIC usulan (ForecastIQ) = Σ total_inventory_cost dari reorder_recommendations tersimpan.
  - TIC baseline (existing) = seri planning perusahaan → BOM breakdown → EOQ per material
    (simetris dgn jalur forecast di ReorderService).
  - savings_pct = (TIC_baseline − TIC_usulan) / TIC_baseline × 100.
"""
from dataclasses import dataclass
from decimal import Decimal

from app.config import get_settings
from app.services.bom_service import BomLine, breakdown_requirements_series
from app.services.reorder_service import compute_eoq, compute_savings_pct
from app.utils.exceptions import ForbiddenRoleError, ForecastRunNotFoundError


def _dec(value) -> Decimal:
    return Decimal(str(round(float(value), 4)))


@dataclass
class CostSummary:
    total_ordering_cost: Decimal
    total_holding_cost: Decimal
    total_inventory_cost: Decimal  # usulan ForecastIQ
    baseline_inventory_cost: Decimal  # existing (planning perusahaan)
    savings_pct: Decimal


def aggregate_proposed(recs) -> tuple[Decimal, Decimal, Decimal]:
    """Jumlahkan ordering/holding/TIC dari reorder_recommendations tersimpan."""
    ordering = sum(float(r.ordering_cost or 0) for r in recs)
    holding = sum(float(r.holding_cost or 0) for r in recs)
    tic = sum(float(r.total_inventory_cost or 0) for r in recs)
    return _dec(ordering), _dec(holding), _dec(tic)


class CostService:
    def __init__(
        self, forecast_repo, reorder_repo, demand_repo, boms, products, ordering_cost=None, holding_cost=None
    ):
        settings = get_settings()
        self._forecast = forecast_repo
        self._reorder = reorder_repo
        self._demand = demand_repo
        self._boms = boms
        self._products = products
        self._ordering = settings.DEFAULT_ORDERING_COST if ordering_cost is None else ordering_cost
        self._holding = settings.DEFAULT_HOLDING_COST_RATE if holding_cost is None else holding_cost

    async def get_cost_summary(self, user_id: str, run_id: str) -> CostSummary:
        await self._require_run(user_id, run_id)

        recs = await self._reorder.list_by_run(run_id)
        ordering, holding, proposed_tic = aggregate_proposed(recs)

        baseline_tic = await self._baseline_tic(run_id)
        savings = compute_savings_pct(float(baseline_tic), float(proposed_tic))

        return CostSummary(
            total_ordering_cost=ordering,
            total_holding_cost=holding,
            total_inventory_cost=proposed_tic,
            baseline_inventory_cost=baseline_tic,
            savings_pct=savings,
        )

    async def _baseline_tic(self, run_id: str) -> Decimal:
        """TIC bila perusahaan pakai seri planning existing (planning → BOM → EOQ per material)."""
        product_planning: dict[str, list[float]] = {}
        bom_lines: list[BomLine] = []

        for result in await self._forecast.list_results(run_id):
            if result.status != "COMPLETED" or result.product_id is None:
                continue
            pid = str(result.product_id)
            product = await self._products.get_by_id(pid)
            code = product.code if product else None
            drows = sorted(
                await self._demand.list_for_product(pid, code), key=lambda r: str(r.period)
            )
            series = [float(r.planning) for r in drows if r.planning is not None]
            if series:
                product_planning[pid] = series
            for bom in await self._boms.list(pid):
                bom_lines.append(BomLine(str(bom.product_id), str(bom.material_id), float(bom.qty_per_unit)))

        material_series = breakdown_requirements_series(product_planning, bom_lines)
        baseline = sum(
            float(compute_eoq(series, self._ordering, self._holding).total_cost)
            for series in material_series.values()
        )
        return _dec(baseline)

    async def _require_run(self, user_id: str, run_id: str):
        run = await self._forecast.get_run(run_id)
        if run is None:
            raise ForecastRunNotFoundError("Forecast run tidak ditemukan.")
        if str(run.user_id) != str(user_id):
            raise ForbiddenRoleError("Anda tidak berhak mengakses run ini.")
        return run
