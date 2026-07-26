"""
InventoryMetricsService (v3.0 Fase 7) — evaluasi kinerja inventory per run,
docs/ARCHITECTURE.md §4 + RECONCILIATION §Fase 7.

Fungsi murni (`fill_rate`, `stock_out_rate`, `service_level`, `inventory_turnover`,
`compute_metrics`) diverifikasi manual (AGENTS.md §3). Orkestrasi menghasilkan 2
scope per produk COMPLETED:
  - baseline  : demand=actual, supply=planning (kinerja EXISTING perusahaan)
  - forecastiq: demand=actual, supply=forecast ForecastIQ (diselaraskan per periode;
                dilewati bila horizon forecast tidak beririsan dgn periode historis).
"""
from dataclasses import dataclass
from decimal import Decimal

from app.models.inventory_metrics import InventoryMetric
from app.utils.exceptions import ForbiddenRoleError, ForecastRunNotFoundError

_EPS = 1e-9


def _dec(value) -> Decimal:
    return Decimal(str(round(float(value), 4)))


@dataclass
class InventoryMetricValues:
    service_level: Decimal
    fill_rate: Decimal
    stock_out_rate: Decimal
    inventory_turnover: Decimal


def fill_rate(demand, supply) -> Decimal:
    """β service level: 1 − Σ kekurangan / Σ demand. Demand 0 → 1 (tak ada yg tak terpenuhi)."""
    total_demand = sum(float(d) for d in demand)
    if total_demand <= 0:
        return _dec(1)
    shortage = sum(max(0.0, float(d) - float(s)) for d, s in zip(demand, supply))
    return _dec(1 - shortage / total_demand)


def stock_out_rate(demand, supply) -> Decimal:
    """Proporsi periode yang mengalami kekurangan (demand > supply)."""
    periods = len(demand)
    if periods == 0:
        return _dec(0)
    stockouts = sum(1 for d, s in zip(demand, supply) if float(d) - float(s) > _EPS)
    return _dec(stockouts / periods)


def service_level(demand, supply) -> Decimal:
    """α service level berbasis siklus: 1 − stock out rate."""
    return _dec(1 - float(stock_out_rate(demand, supply)))


def inventory_turnover(demand, supply) -> Decimal:
    """Σ demand ÷ persediaan rata-rata (supply sebagai proksi). Supply rata-rata 0 → 0."""
    if not supply:
        return _dec(0)
    avg_supply = sum(float(s) for s in supply) / len(supply)
    if avg_supply <= 0:
        return _dec(0)
    return _dec(sum(float(d) for d in demand) / avg_supply)


def compute_metrics(demand, supply) -> InventoryMetricValues:
    return InventoryMetricValues(
        service_level=service_level(demand, supply),
        fill_rate=fill_rate(demand, supply),
        stock_out_rate=stock_out_rate(demand, supply),
        inventory_turnover=inventory_turnover(demand, supply),
    )


class InventoryMetricsService:
    def __init__(self, forecast_repo, demand_repo, products, metrics_repo):
        self._forecast = forecast_repo
        self._demand = demand_repo
        self._products = products
        self._metrics = metrics_repo

    async def compute_for_run(self, user_id: str, run_id: str) -> list[InventoryMetric]:
        run = await self._require_run(user_id, run_id)
        rows: list[InventoryMetric] = []

        for result in await self._forecast.list_results(run_id):
            if result.status != "COMPLETED" or result.product_id is None:
                continue

            product = await self._products.get_by_id(str(result.product_id))
            code = product.code if product else None
            drows = sorted(
                await self._demand.list_for_product(str(result.product_id), code),
                key=lambda r: str(r.period),
            )

            # baseline: actual vs planning (periode dengan planning terisi)
            base = [(float(r.actual), float(r.planning)) for r in drows if r.planning is not None]
            if base:
                rows.append(
                    self._row(run.id, result.product_id, "baseline", [d for d, _ in base], [s for _, s in base])
                )

            # forecastiq: actual vs forecast, selaras per periode (date)
            fmap = {
                str(p.get("date"))[:10]: float(p.get("value", 0)) for p in (result.forecast_data or [])
            }
            aligned = [(float(r.actual), fmap[str(r.period)[:10]]) for r in drows if str(r.period)[:10] in fmap]
            if aligned:
                rows.append(
                    self._row(run.id, result.product_id, "forecastiq", [d for d, _ in aligned], [s for _, s in aligned])
                )

        return await self._metrics.replace_for_run(str(run_id), rows)

    def _row(self, run_id, product_id, scope, demand, supply) -> InventoryMetric:
        m = compute_metrics(demand, supply)
        return InventoryMetric(
            run_id=run_id,
            target_type="product",
            target_id=product_id,
            scope=scope,
            service_level=m.service_level,
            fill_rate=m.fill_rate,
            stock_out_rate=m.stock_out_rate,
            inventory_turnover=m.inventory_turnover,
        )

    async def _require_run(self, user_id: str, run_id: str):
        run = await self._forecast.get_run(run_id)
        if run is None:
            raise ForecastRunNotFoundError("Forecast run tidak ditemukan.")
        if str(run.user_id) != str(user_id):
            raise ForbiddenRoleError("Anda tidak berhak mengakses run ini.")
        return run
