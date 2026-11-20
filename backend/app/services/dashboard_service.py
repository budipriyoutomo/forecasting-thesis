"""
DashboardService — ringkasan untuk halaman dashboard (Fase 7, diperluas Fase 9).

Agregasi lintas domain: jumlah material, run forecast terakhir + akurasi
(MASE/MAPE rata-rata), distribusi status reorder, jumlah override terbaru.
Fase 9 (diperluas, additive — RECONCILIATION §Fase 9): total biaya persediaan
(TIC) run terakhir, indikator kapasitas gudang, dan ringkasan metrik inventory
per scope (baseline vs forecastiq). Semua dibaca lewat repository, tidak query
inline di endpoint. Repo warehouse/inventory-metrics opsional (default None) →
widget-nya `None` bila belum tersedia, tanpa memutus dashboard v2.0.

CR v3.6 §1/§3 (additive): `latest_run` + created_at/created_by/n_pending_selection/
total_inventory_cost_baseline/savings_pct (baseline lewat CostService — rumus tidak
diduplikasi), `warehouse.products_over` (maks 10, kelebihan terbesar dulu), dan
`attention` (produk gagal, material tanpa data biaya, periode kekurangan stok).
"""
import logging

from app.utils.exceptions import AppError

log = logging.getLogger(__name__)

MAX_PRODUCTS_OVER = 10
MISSING_COST_STATUSES = ("MISSING_UNIT_PRICE", "MISSING_HOLDING_RATE")

METRIC_FIELDS = ("service_level", "fill_rate", "stock_out_rate", "inventory_turnover")


def _avg(values):
    values = [v for v in values if v is not None]
    return round(sum(values) / len(values), 4) if values else None


def _summarize_metrics(rows) -> dict | None:
    """Rata-rata 4 metrik per scope (baseline / forecastiq)."""
    if not rows:
        return None
    by_scope: dict[str, list] = {}
    for row in rows:
        by_scope.setdefault(row.scope, []).append(row)
    return {
        scope: {f: _avg([float(getattr(i, f)) for i in items]) for f in METRIC_FIELDS}
        for scope, items in by_scope.items()
    }


class DashboardService:
    def __init__(
        self,
        materials,
        forecast_repo,
        reorder_repo,
        override_repo,
        warehouse_repo=None,
        inventory_metrics_repo=None,
        products=None,
        projections=None,
        cost_service=None,
    ):
        self._materials = materials
        self._forecast = forecast_repo
        self._reorder = reorder_repo
        self._override = override_repo
        self._warehouse = warehouse_repo
        self._inv_metrics = inventory_metrics_repo
        self._products = products  # CR v3.6 §3 — kode & nama produk melebihi kapasitas
        self._projections = projections  # CR v3.6 §3 — periode kekurangan stok
        self._cost = cost_service  # CR v3.6 §3 — TIC baseline & penghematan

    async def _latest_run(self):
        """(run, label pembuat) run terbaru — list_runs(1) supaya pembuat ikut terbaca."""
        rows = await self._forecast.list_runs(1)
        return rows[0] if rows else (None, None)

    async def _baseline(self, user_id: str, run_id: str) -> tuple[float | None, float | None]:
        if self._cost is None:
            return None, None
        try:
            cost = await self._cost.get_cost_summary(user_id, run_id)
        except AppError:  # mis. BOM_NOT_FOUND — widget kosong, dashboard tetap jalan
            log.info("Baseline TIC run %s tidak bisa dihitung", run_id, exc_info=True)
            return None, None
        return round(float(cost.baseline_inventory_cost), 4), round(float(cost.savings_pct), 4)

    async def _products_over(self, details) -> list[dict]:
        over = sorted(
            (d for d in details if not d["is_within_capacity"]),
            key=lambda d: float(d["required_qty"]) - float(d["capacity_qty"]),
            reverse=True,
        )[:MAX_PRODUCTS_OVER]
        rows = []
        for d in over:
            product = await self._products.get_by_id(d["product_id"]) if self._products else None
            rows.append(
                {
                    "product_id": str(d["product_id"]),
                    "code": getattr(product, "code", None),
                    "name": getattr(product, "name", None),
                    "excess_qty": round(float(d["required_qty"]) - float(d["capacity_qty"]), 4),
                }
            )
        return rows

    async def summary(self, user_id: str) -> dict:
        materials = await self._materials.list()
        # CR v3.5 §3.4 Opsi A: run terakhir organisasi, bukan milik user.
        latest_run, created_by = await self._latest_run()

        latest_run_summary = None
        reorder_counts = {"urgent": 0, "safe": 0, "overstock": 0}
        warehouse = None
        inventory_metrics = None
        attention = None

        if latest_run is not None:
            results = await self._forecast.list_results(str(latest_run.id))
            completed = [r for r in results if r.status == "COMPLETED"]
            avg_mase = _avg([float(r.mase) for r in completed if r.mase is not None])
            avg_mape = _avg([float(r.mape) for r in completed if getattr(r, "mape", None) is not None])
            # 21 Nov 2026 — metrik pengujian peramalan yang ditampilkan: MAD, MFE, MAPE
            avg_mad = _avg([float(r.mad) for r in completed if getattr(r, "mad", None) is not None])
            avg_mfe = _avg([float(r.mfe) for r in completed if getattr(r, "mfe", None) is not None])

            recs = await self._reorder.list_by_run(str(latest_run.id))
            for rec in recs:
                if rec.status in reorder_counts:
                    reorder_counts[rec.status] += 1
            total_inventory_cost = sum(float(getattr(rec, "total_inventory_cost", 0) or 0) for rec in recs)
            baseline, savings = await self._baseline(user_id, str(latest_run.id)) if recs else (None, None)
            created_at = getattr(latest_run, "created_at", None)

            latest_run_summary = {
                "run_id": str(latest_run.id),
                "status": latest_run.status,
                "n_products": len(results),  # forecast_results per produk (CR v3.5 §4)
                "n_completed": len(completed),
                "n_failed": len(results) - len(completed),
                "avg_mase": avg_mase,
                "avg_mape": avg_mape,
                "avg_mad": avg_mad,
                "avg_mfe": avg_mfe,
                "total_inventory_cost": round(total_inventory_cost, 4),
                "created_at": created_at.isoformat() if created_at else None,
                "created_by": created_by,
                "n_pending_selection": sum(
                    1 for r in completed if getattr(r, "selection_status", None) == "PENDING_SELECTION"
                ),
                "total_inventory_cost_baseline": baseline,
                "savings_pct": savings,
            }

            shortage_rows = await self._projections.list_by_run(str(latest_run.id)) if self._projections else []
            attention = {
                "n_failed_products": len(results) - len(completed),
                "n_missing_cost_data": sum(
                    1 for rec in recs if getattr(rec, "item_status", None) in MISSING_COST_STATUSES
                ),
                "n_shortage_periods": sum(
                    1 for row in shortage_rows if row.scenario == "proposed" and (row.shortage_qty or 0) > 0
                ),
            }

            if self._warehouse is not None:
                v = await self._warehouse.get_for_run(str(latest_run.id))
                if v is not None:
                    warehouse = {
                        "is_within_capacity": v.is_within_capacity,
                        "n_products_over": sum(1 for d in v.details if not d["is_within_capacity"]),
                        "n_products_checked": len(v.details),
                        "products_over": await self._products_over(v.details),
                    }

            if self._inv_metrics is not None:
                inventory_metrics = _summarize_metrics(await self._inv_metrics.list_by_run(str(latest_run.id)))

        recent_overrides = await self._override.list_recent(limit=5)

        return {
            "n_materials": len(materials),
            "latest_run": latest_run_summary,
            "reorder_status_counts": reorder_counts,
            "n_recent_overrides": len(recent_overrides),
            "warehouse": warehouse,
            "inventory_metrics": inventory_metrics,
            "attention": attention,
        }
