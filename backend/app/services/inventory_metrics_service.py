"""
InventoryMetricsService (v3.0 Fase 7) — evaluasi kinerja inventory per run,
docs/ARCHITECTURE.md §4 + RECONCILIATION §Fase 7.

Fungsi murni (`fill_rate`, `stock_out_rate`, `service_level`, `inventory_turnover`,
`compute_metrics`) diverifikasi manual (AGENTS.md §3). Orkestrasi menghasilkan 2
scope per produk COMPLETED:
  - baseline  : demand=actual, supply=planning (kinerja EXISTING perusahaan)
  - forecastiq: demand=actual, supply=forecast ForecastIQ (diselaraskan per periode;
                dilewati bila horizon forecast tidak beririsan dgn periode historis).

Definisi metrik (dikunci Fase 11.10, v3.3 — istilah docx thesis; sumber: definisi
standar yang disepakati di RECONCILIATION §Fase 7 karena docx belum memuat rumusnya):
  Fulfilment rate (β) = 1 − Σ kekurangan ÷ Σ demand          (berbasis QTY; field `fill_rate`)
  Stock out rate      = periode dgn kekurangan ÷ jumlah periode (berbasis PERIODE)
  Service level (α)   = 1 − stock out rate                     (berbasis siklus/periode)
  Inventory turnover  = Σ demand ÷ persediaan rata-rata
Dipakai SAMA oleh scope produk (`compute_metrics`) dan material (`material_metrics`).
⛔ Bila docx nanti mendefinisikan stock out rate berbasis qty → tambah opsi di
Pengaturan Forecast, JANGAN ganti definisi diam-diam (TODO-v3 Fase 11.10).

Fase 11.7 (REVISI_V2 §3.9): scope MATERIAL dari proyeksi stok (tahap 4 thesis) —
fulfillment/service level, stockout rate, turnover, inventory days, shortage cost.
Shortage cost = qty produk tak terpenuhi × harga produk (`selling_price`). Kekurangan material bersama
(mis. Bottle untuk 6 SKU) dialokasikan ke produk proporsional porsi kebutuhannya
sepanjang horizon, lalu dibagi qty BOM → unit produk (asumsi dicatat di thesis).
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
    inventory_days: Decimal | None = None


def inventory_days(avg_inventory: float, avg_daily_usage: float) -> float | None:
    """Inventory turnover (hari) thesis = rata-rata persediaan ÷ rata-rata pemakaian per hari."""
    if float(avg_daily_usage) <= 0:
        return None
    return float(avg_inventory) / float(avg_daily_usage)


def shortage_cost(units_by_product: dict, selling_price: dict) -> float:
    """Σ qty produk tak terpenuhi × harga produk; produk tanpa harga dilewati."""
    return sum(
        float(units) * float(selling_price[pid])
        for pid, units in units_by_product.items()
        if selling_price.get(pid) is not None
    )


def allocate_shortage(shortage_qty: float, requirement_by_product: dict, qty_per_unit: dict) -> dict:
    """Kekurangan material → unit produk tak terpenuhi, proporsional porsi kebutuhan."""
    total = sum(float(v) for v in requirement_by_product.values())
    if total <= 0:
        return {}
    return {
        pid: float(shortage_qty) * float(req) / total / float(qty_per_unit[pid])
        for pid, req in requirement_by_product.items()
        if float(qty_per_unit.get(pid, 0)) > 0
    }


def material_metrics(rows, days_per_period: float) -> InventoryMetricValues:
    """Metrik satu material × skenario dari baris proyeksi stok (urut periode).
    Definisi identik dgn `compute_metrics` (demand = usage, kekurangan = shortage_qty)."""
    usage = sum(float(r.usage_qty) for r in rows)
    shortage = sum(float(r.shortage_qty) for r in rows)
    n = len(rows)
    avg_stock = sum((float(r.opening_qty) + float(r.ending_qty)) / 2 for r in rows) / n if n else 0.0
    stockouts = sum(1 for r in rows if float(r.shortage_qty) > _EPS)
    days = inventory_days(avg_stock, usage / (n * float(days_per_period))) if n and days_per_period else None
    stock_out = stockouts / n if n else 0.0
    return InventoryMetricValues(
        service_level=_dec(1 - stock_out),
        fill_rate=_dec(1 - shortage / usage) if usage > 0 else _dec(1),
        stock_out_rate=_dec(stock_out),
        inventory_turnover=_dec(usage / avg_stock) if avg_stock > 0 else _dec(0),
        inventory_days=_dec(days) if days is not None else None,
    )


def fill_rate(demand, supply) -> Decimal:
    """Fulfilment rate (β): 1 − Σ kekurangan / Σ demand (berbasis qty). Demand 0 → 1."""
    total_demand = sum(float(d) for d in demand)
    if total_demand <= 0:
        return _dec(1)
    shortage = sum(max(0.0, float(d) - float(s)) for d, s in zip(demand, supply))
    return _dec(1 - shortage / total_demand)


def stock_out_rate(demand, supply) -> Decimal:
    """Stock out rate: proporsi PERIODE yang mengalami kekurangan (demand > supply), bukan qty."""
    periods = len(demand)
    if periods == 0:
        return _dec(0)
    stockouts = sum(1 for d, s in zip(demand, supply) if float(d) - float(s) > _EPS)
    return _dec(stockouts / periods)


def service_level(demand, supply) -> Decimal:
    """Service level (α) berbasis siklus/periode: 1 − stock out rate."""
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
    def __init__(self, forecast_repo, demand_repo, products, metrics_repo, projections=None, boms=None):
        self._forecast = forecast_repo
        self._demand = demand_repo
        self._products = products
        self._metrics = metrics_repo
        # Fase 11.7 — proyeksi stok (scope material) & BOM (alokasi shortage cost)
        self._projections = projections
        self._boms = boms

    async def compute_for_run(self, user_id: str, run_id: str) -> list[InventoryMetric]:
        run = await self._require_run(user_id, run_id)
        rows: list[InventoryMetric] = []
        prices: dict[str, object] = {}
        requirement: dict[str, dict[str, float]] = {}  # material → {produk: kebutuhan horizon}
        qty_per_unit: dict[str, dict[str, float]] = {}
        forecast_dates: list = []

        for result in await self._forecast.list_results(run_id):
            if result.status != "COMPLETED" or result.product_id is None:
                continue

            product = await self._products.get_by_id(str(result.product_id))
            code = product.code if product else None
            pid = str(result.product_id)
            prices[pid] = getattr(product, "selling_price", None)
            total_forecast = sum(float(p.get("value", 0)) for p in (result.forecast_data or []))
            if not forecast_dates:
                forecast_dates = [p.get("date") for p in (result.forecast_data or [])]
            for bom in (await self._boms.list(pid)) if self._boms else []:
                mid = str(bom.material_id)
                requirement.setdefault(mid, {})[pid] = total_forecast * float(bom.qty_per_unit)
                qty_per_unit.setdefault(mid, {})[pid] = float(bom.qty_per_unit)
            drows = sorted(
                await self._demand.list_for_product(str(result.product_id), code),
                key=lambda r: str(r.period),
            )

            # baseline: actual vs planning (periode dengan planning terisi)
            base = [(float(r.actual), float(r.planning)) for r in drows if r.planning is not None]
            if base:
                rows.append(
                    self._row(
                        run.id, result.product_id, "baseline", [d for d, _ in base], [s for _, s in base], prices[pid]
                    )
                )

            # forecastiq: actual vs forecast, selaras per periode (date)
            fmap = {
                str(p.get("date"))[:10]: float(p.get("value", 0)) for p in (result.forecast_data or [])
            }
            aligned = [(float(r.actual), fmap[str(r.period)[:10]]) for r in drows if str(r.period)[:10] in fmap]
            if aligned:
                rows.append(
                    self._row(
                        run.id, result.product_id, "forecastiq",
                        [d for d, _ in aligned], [s for _, s in aligned], prices[pid],
                    )
                )

        rows.extend(await self._material_rows(run, requirement, qty_per_unit, prices, forecast_dates))
        return await self._metrics.replace_for_run(str(run_id), rows)

    async def _material_rows(self, run, requirement, qty_per_unit, prices, forecast_dates) -> list:
        if self._projections is None:
            return []
        from app.services.reorder_service import days_in_period

        days = days_in_period(forecast_dates)
        grouped: dict[tuple[str, str], list] = {}
        for p in await self._projections.list_by_run(str(run.id)):
            grouped.setdefault((str(p.material_id), p.scenario), []).append(p)

        out = []
        for (mid, scenario), proj in sorted(grouped.items()):
            proj.sort(key=lambda r: r.period)
            m = material_metrics(proj, days)
            short = sum(float(r.shortage_qty) for r in proj)
            units = allocate_shortage(short, requirement.get(mid, {}), qty_per_unit.get(mid, {}))
            out.append(
                InventoryMetric(
                    run_id=run.id,
                    target_type="material",
                    target_id=mid,
                    scope="forecastiq" if scenario == "proposed" else "baseline",
                    service_level=m.service_level,
                    fill_rate=m.fill_rate,
                    stock_out_rate=m.stock_out_rate,
                    inventory_turnover=m.inventory_turnover,
                    inventory_days=m.inventory_days,
                    shortage_cost=_dec(shortage_cost(units, prices)),
                )
            )
        return out

    def _row(self, run_id, product_id, scope, demand, supply, selling_price=None) -> InventoryMetric:
        m = compute_metrics(demand, supply)
        unmet = sum(max(0.0, float(d) - float(s)) for d, s in zip(demand, supply))
        return InventoryMetric(
            run_id=run_id,
            target_type="product",
            target_id=product_id,
            scope=scope,
            service_level=m.service_level,
            fill_rate=m.fill_rate,
            stock_out_rate=m.stock_out_rate,
            inventory_turnover=m.inventory_turnover,
            shortage_cost=_dec(shortage_cost({"p": unmet}, {"p": selling_price})),
        )

    async def _require_run(self, user_id: str, run_id: str):
        run = await self._forecast.get_run(run_id)
        if run is None:
            raise ForecastRunNotFoundError("Forecast run tidak ditemukan.")
        if str(run.user_id) != str(user_id):
            raise ForbiddenRoleError("Anda tidak berhak mengakses run ini.")
        return run
