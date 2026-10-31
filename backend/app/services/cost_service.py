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

Fase 10 (2 Oktober 2026): S & H baseline dari template biaya aktif (fallback env /
argumen konstruktor), plus `purchase_cost` = Σ kebutuhan material forecast × harga
beli — INFORMASI saja, tidak masuk TIC (RECONCILIATION §"Konsolidasi Master Data").
"""
from dataclasses import dataclass
from decimal import Decimal
from types import SimpleNamespace

from app.config import get_settings
from app.services.bom_service import BomLine, breakdown_requirements_series
from app.services.cost_template_service import load_cost_params
from app.services.reorder_service import DEFAULT_EOQ_METHOD, choose_eoq, compute_savings_pct, days_in_period
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
    # Fase 10 — additive
    purchase_cost: Decimal = Decimal(0)  # informasi, tidak masuk TIC
    n_materials_without_price: int = 0
    cost_source: str = "env"  # "template" | "env" — sumber S & H baseline
    cost_template_name: str | None = None
    eoq_method: str = DEFAULT_EOQ_METHOD  # Fase 11.4 — metode yang diminta master data
    shortage_cost: Decimal | None = None  # Fase 11.7 — dari inventory_metrics material (None = belum dihitung)
    baseline_shortage_cost: Decimal | None = None


def aggregate_proposed(recs) -> tuple[Decimal, Decimal, Decimal]:
    """Jumlahkan ordering/holding/TIC dari reorder_recommendations tersimpan."""
    ordering = sum(float(r.ordering_cost or 0) for r in recs)
    holding = sum(float(r.holding_cost or 0) for r in recs)
    tic = sum(float(r.total_inventory_cost or 0) for r in recs)
    return _dec(ordering), _dec(holding), _dec(tic)


class CostService:
    def __init__(
        self,
        forecast_repo,
        reorder_repo,
        demand_repo,
        boms,
        products,
        ordering_cost=None,
        holding_cost=None,
        cost_templates=None,
        materials=None,
        settings=None,
        metrics_repo=None,
    ):
        app_settings = get_settings()
        self._forecast = forecast_repo
        self._reorder = reorder_repo
        self._demand = demand_repo
        self._boms = boms
        self._products = products
        self._cost_templates = cost_templates
        self._materials = materials
        self._settings = settings  # Fase 11.4 — metode EOQ (master data)
        self._metrics = metrics_repo  # Fase 11.7 — shortage cost material
        # Fallback bila tak ada template aktif: argumen eksplisit (test) atau env.
        self._fallback = SimpleNamespace(
            DEFAULT_ORDERING_COST=app_settings.DEFAULT_ORDERING_COST if ordering_cost is None else ordering_cost,
            DEFAULT_HOLDING_COST_RATE=app_settings.DEFAULT_HOLDING_COST_RATE if holding_cost is None else holding_cost,
        )

    async def get_cost_summary(self, user_id: str, run_id: str) -> CostSummary:
        await self._require_run(user_id, run_id)
        cost = await load_cost_params(self._cost_templates, self._fallback)

        recs = await self._reorder.list_by_run(run_id)
        ordering, holding, proposed_tic = aggregate_proposed(recs)

        method = await self._settings.eoq_method() if self._settings else DEFAULT_EOQ_METHOD
        baseline_tic = await self._baseline_tic(run_id, cost, method)
        savings = compute_savings_pct(float(baseline_tic), float(proposed_tic))
        purchase_cost, n_without_price = await self._purchase_cost(run_id)

        return CostSummary(
            total_ordering_cost=ordering,
            total_holding_cost=holding,
            total_inventory_cost=proposed_tic,
            baseline_inventory_cost=baseline_tic,
            savings_pct=savings,
            purchase_cost=purchase_cost,
            n_materials_without_price=n_without_price,
            cost_source=cost.source,
            cost_template_name=cost.template_name,
            eoq_method=method,
            **await self._shortage(run_id),
        )

    async def _shortage(self, run_id: str) -> dict:
        rows = [
            r for r in (await self._metrics.list_by_run(run_id) if self._metrics else [])
            if r.target_type == "material" and getattr(r, "shortage_cost", None) is not None
        ]
        if not rows:
            return {}
        total = {s: sum(float(r.shortage_cost) for r in rows if r.scope == s) for s in ("forecastiq", "baseline")}
        return {"shortage_cost": _dec(total["forecastiq"]), "baseline_shortage_cost": _dec(total["baseline"])}

    async def _purchase_cost(self, run_id: str) -> tuple[Decimal, int]:
        """Σ kebutuhan material sepanjang horizon forecast × harga beli; material tanpa harga dilewati."""
        product_series: dict[str, list[float]] = {}
        bom_lines: list[BomLine] = []
        for result in await self._forecast.list_results(run_id):
            fdata = getattr(result, "forecast_data", None) or []
            if result.status != "COMPLETED" or result.product_id is None or not fdata:
                continue
            pid = str(result.product_id)
            product_series[pid] = [float(p.get("value", 0)) for p in fdata]
            for bom in await self._boms.list(pid):
                bom_lines.append(BomLine(str(bom.product_id), str(bom.material_id), float(bom.qty_per_unit)))

        total, missing = Decimal(0), 0
        for material_id, series in breakdown_requirements_series(product_series, bom_lines).items():
            material = await self._materials.get_by_id(material_id) if self._materials else None
            price = getattr(material, "unit_price", None) if material is not None else None
            if price is None:
                missing += 1
                continue
            total += Decimal(str(sum(series))) * Decimal(str(price))
        return _dec(total), missing

    async def _baseline_tic(self, run_id: str, cost, method: str) -> Decimal:
        """TIC bila perusahaan pakai seri planning existing (planning → BOM → EOQ per material).

        Fase 11.4: metode EOQ per material dipilih dengan aturan yang SAMA seperti usulan
        (`choose_eoq`: klasik bila harga & i ada), supaya basis biaya (tahunan vs horizon)
        kedua sisi setara.
        """
        product_planning: dict[str, list[float]] = {}
        bom_lines: list[BomLine] = []
        planning_dates: list = []

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
                if not planning_dates:
                    planning_dates = [str(r.period) for r in drows if r.planning is not None]
            for bom in await self._boms.list(pid):
                bom_lines.append(BomLine(str(bom.product_id), str(bom.material_id), float(bom.qty_per_unit)))

        material_series = breakdown_requirements_series(product_planning, bom_lines)
        days = days_in_period(planning_dates)
        baseline = 0.0
        for material_id, series in material_series.items():
            material = await self._materials.get_by_id(material_id) if self._materials else None
            price = getattr(material, "unit_price", None) if material is not None else None
            baseline += choose_eoq(series, days, method, price, cost.holding_rate_pct, cost).total_cost
        return _dec(baseline)

    async def _require_run(self, user_id: str, run_id: str):
        run = await self._forecast.get_run(run_id)
        if run is None:
            raise ForecastRunNotFoundError("Forecast run tidak ditemukan.")
        if str(run.user_id) != str(user_id):
            raise ForbiddenRoleError("Anda tidak berhak mengakses run ini.")
        return run
