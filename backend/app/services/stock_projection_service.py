"""
StockProjectionService (Fase 11.6, 30 Oktober 2026) — tahap 3 alur thesis: proyeksi stok
material per periode horizon & utilisasi gudang (REVISI_V2 §3.2/§3.3, Keputusan #1/#3).

Per periode t:
  pre      = opening + receipt − usage
  order    = OrderPolicy.order_qty(pre) — bila pre ≤ ROP: qty sesuai `order_qty_policy`
             (n × EOQ | order-up-to), else 0. ROP & qty pesan dari SUMBER TUNGGAL
             `reorder_service` (baris `reorder_recommendations` run ini, Fase 11.9 v3.3),
             jadi identik dengan tabel Reorder untuk stok yang sama.
             ASUMSI: pesanan tiba di periode yang sama (lead time < 1 periode bulanan) —
             batasan penelitian thesis.
  ending   = max(0, pre + order);  shortage = max(0, −(pre + order))
  opening[t+1] = ending[t]
  utilisasi = stok ÷ kapasitas material × 100% (stok awal & stok akhir)

Dua skenario (Keputusan #3): `proposed` — pemakaian = forecast ForecastIQ × BOM;
`baseline` — pemakaian = planning perusahaan × BOM pada periode yang sama (hanya bila
planning untuk periode horizon tersedia). Kapasitas melebihi → flag, bukan error (#17).
"""
from dataclasses import dataclass
from datetime import date

import pandas as pd

from app.models.stock_projection import StockProjection
from app.services.bom_service import BomLine, breakdown_requirements_series
from app.services.reorder_service import OrderPolicy, order_policy_from_rec
from app.services.forecasting.preprocessing import future_timestamps, infer_period_delta
from app.utils.exceptions import ForbiddenRoleError, ForecastRunNotFoundError

SCENARIOS = ("proposed", "baseline")


@dataclass
class ProjectionRow:
    opening_qty: float
    receipt_qty: float
    usage_qty: float
    order_qty: float
    ending_qty: float
    shortage_qty: float
    utilization_opening_pct: float | None
    utilization_ending_pct: float | None
    is_within_capacity: bool | None


def _util(qty: float, capacity: float | None) -> float | None:
    return qty / capacity * 100 if capacity else None


def project_stock(opening, receipts, usage, policy: OrderPolicy | None, capacity) -> list[ProjectionRow]:
    """`policy` None (material tanpa rekomendasi reorder) → tidak pernah memesan."""
    rows: list[ProjectionRow] = []
    stock = float(opening)
    cap = float(capacity) if capacity else None
    for receipt, use in zip(receipts, usage):
        start = stock
        pre = start + float(receipt) - float(use)
        order = policy.order_qty(pre) if policy is not None else 0.0
        after = pre + order
        ending, shortage = max(0.0, after), max(0.0, -after)
        rows.append(
            ProjectionRow(
                opening_qty=start,
                receipt_qty=float(receipt),
                usage_qty=float(use),
                order_qty=order,
                ending_qty=ending,
                shortage_qty=shortage,
                utilization_opening_pct=_util(start, cap),
                utilization_ending_pct=_util(ending, cap),
                is_within_capacity=(ending <= cap) if cap else None,
            )
        )
        stock = ending
    return rows


def bucket_by_period(periods: list[date], items: list[tuple[date, float]]) -> list[float]:
    """Jumlahkan (tanggal, qty) ke periode [p_t, p_{t+1}). Tanggal sebelum periode pertama
    masuk periode pertama (kedatangan setelah snapshot, sebelum horizon); di luar horizon dibuang."""
    if not periods:
        return []
    ts = [pd.Timestamp(p) for p in periods]
    delta = infer_period_delta(pd.DatetimeIndex(ts)) if len(ts) > 1 else pd.Timedelta(days=31)
    end = future_timestamps(ts[-1], 1, delta)[0]
    buckets = [0.0] * len(ts)
    for when, qty in items:
        t = pd.Timestamp(when)
        if t >= end:
            continue
        idx = max(i for i, start in enumerate(ts) if start <= t) if t >= ts[0] else 0
        buckets[idx] += float(qty)
    return buckets


class StockProjectionService:
    def __init__(
        self, projection_repo, forecast_repo, reorder_repo, boms, demand_repo, products, warehouse_configs,
        stock, receipts, reorder_service=None, factory=StockProjection,
    ):
        self._repo = projection_repo
        self._forecast = forecast_repo
        self._reorder = reorder_repo
        self._boms = boms
        self._demand = demand_repo
        self._products = products
        self._configs = warehouse_configs
        self._stock = stock
        self._receipts = receipts
        self._reorder_service = reorder_service
        self._factory = factory

    async def generate_for_run(self, user_id: str, run_id: str) -> list:
        run = await self._require_run(user_id, run_id)
        periods, forecast_series, planning_series, bom_lines = await self._series(run_id)
        if not periods:
            await self._repo.replace_for_run(str(run_id), [])
            return []

        recs = {str(r.material_id): r for r in await self._reorder.list_by_run(run_id)}
        if not recs and self._reorder_service is not None:
            recs = {str(r.material_id): r for r in await self._reorder_service.generate_for_run(user_id, run_id)}

        capacity = {
            str(c.material_id): float(c.capacity_qty)
            for c in await self._configs.list()
            if getattr(c, "item_type", "product") == "material"
        }
        opening = await self._stock.latest_stock(as_of=periods[0])
        receipt_rows = await self._receipts.list(date_to=None)

        rows = []
        for scenario, product_series in (("proposed", forecast_series), ("baseline", planning_series)):
            if not product_series:
                continue
            for material_id, usage in breakdown_requirements_series(product_series, bom_lines).items():
                usage = (usage + [0.0] * len(periods))[: len(periods)]
                rec = recs.get(material_id)
                receipts = bucket_by_period(
                    periods,
                    [(r.expected_date, r.qty) for r in receipt_rows if str(r.material_id) == material_id],
                )
                policy = order_policy_from_rec(rec) if rec else None
                projected = project_stock(
                    opening.get(material_id, (None, 0.0))[1], receipts, usage, policy, capacity.get(material_id)
                )
                for period, p in zip(periods, projected):
                    rows.append(
                        self._factory(
                            run_id=run.id, material_id=material_id, scenario=scenario, period=period,
                            opening_qty=p.opening_qty, receipt_qty=p.receipt_qty, usage_qty=p.usage_qty,
                            order_qty=p.order_qty, ending_qty=p.ending_qty, shortage_qty=p.shortage_qty,
                            capacity_qty=capacity.get(material_id),
                            utilization_opening_pct=p.utilization_opening_pct,
                            utilization_ending_pct=p.utilization_ending_pct,
                            is_within_capacity=p.is_within_capacity,
                        )
                    )
        await self._repo.replace_for_run(str(run_id), rows)
        return rows

    async def list_for_run(self, user_id: str, run_id: str, scenario: str | None = None):
        await self._require_run(user_id, run_id)
        rows = await self._repo.list_by_run(run_id)
        return [r for r in rows if scenario is None or r.scenario == scenario]

    async def _series(self, run_id: str):
        """Periode horizon + deret forecast & planning per produk (planning hanya bila
        tersedia untuk SELURUH periode horizon), + baris BOM."""
        periods: list[date] = []
        forecast_series: dict[str, list[float]] = {}
        planning_series: dict[str, list[float]] = {}
        bom_lines: list[BomLine] = []
        for result in await self._forecast.list_results(run_id):
            fdata = getattr(result, "forecast_data", None) or []
            if result.status != "COMPLETED" or not fdata or result.product_id is None:
                continue
            pid = str(result.product_id)
            dates = [pd.Timestamp(p["date"]).date() for p in fdata if p.get("date")]
            if not periods and len(dates) == len(fdata):
                periods = dates
            forecast_series[pid] = [float(p.get("value", 0)) for p in fdata]
            product = await self._products.get_by_id(pid)
            planning = {
                pd.Timestamp(str(r.period)).date(): float(r.planning)
                for r in await self._demand.list_for_product(pid, getattr(product, "code", None))
                if r.planning is not None
            }
            if periods and all(p in planning for p in periods):
                planning_series[pid] = [planning[p] for p in periods]
            for bom in await self._boms.list(pid):
                bom_lines.append(BomLine(str(bom.product_id), str(bom.material_id), float(bom.qty_per_unit)))
        return periods, forecast_series, planning_series, bom_lines

    async def _require_run(self, user_id: str, run_id: str):
        run = await self._forecast.get_run(run_id)
        if run is None:
            raise ForecastRunNotFoundError("Forecast run tidak ditemukan.")
        if str(run.user_id) != str(user_id):
            raise ForbiddenRoleError("Anda tidak berhak mengakses run ini.")
        return run
