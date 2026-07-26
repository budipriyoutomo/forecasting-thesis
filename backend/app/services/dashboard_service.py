"""
DashboardService — ringkasan untuk halaman dashboard (Fase 7, diperluas Fase 9).

Agregasi lintas domain: jumlah material, run forecast terakhir + akurasi
(MASE/MAPE rata-rata), distribusi status reorder, jumlah override terbaru.
Fase 9 (diperluas, additive — RECONCILIATION §Fase 9): total biaya persediaan
(TIC) run terakhir, indikator kapasitas gudang, dan ringkasan metrik inventory
per scope (baseline vs forecastiq). Semua dibaca lewat repository, tidak query
inline di endpoint. Repo warehouse/inventory-metrics opsional (default None) →
widget-nya `None` bila belum tersedia, tanpa memutus dashboard v2.0.
"""

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
        self, materials, forecast_repo, reorder_repo, override_repo, warehouse_repo=None, inventory_metrics_repo=None
    ):
        self._materials = materials
        self._forecast = forecast_repo
        self._reorder = reorder_repo
        self._override = override_repo
        self._warehouse = warehouse_repo
        self._inv_metrics = inventory_metrics_repo

    async def summary(self, user_id: str) -> dict:
        materials = await self._materials.list()
        latest_run = await self._forecast.get_latest_run_for_user(user_id)

        latest_run_summary = None
        reorder_counts = {"urgent": 0, "safe": 0, "overstock": 0}
        warehouse = None
        inventory_metrics = None

        if latest_run is not None:
            results = await self._forecast.list_results(str(latest_run.id))
            completed = [r for r in results if r.status == "COMPLETED"]
            avg_mase = _avg([float(r.mase) for r in completed if r.mase is not None])
            avg_mape = _avg([float(r.mape) for r in completed if getattr(r, "mape", None) is not None])

            recs = await self._reorder.list_by_run(str(latest_run.id))
            for rec in recs:
                if rec.status in reorder_counts:
                    reorder_counts[rec.status] += 1
            total_inventory_cost = sum(float(getattr(rec, "total_inventory_cost", 0) or 0) for rec in recs)

            latest_run_summary = {
                "run_id": str(latest_run.id),
                "status": latest_run.status,
                "n_materials": len(results),
                "n_completed": len(completed),
                "n_failed": len(results) - len(completed),
                "avg_mase": avg_mase,
                "avg_mape": avg_mape,
                "total_inventory_cost": round(total_inventory_cost, 4),
            }

            if self._warehouse is not None:
                v = await self._warehouse.get_for_run(str(latest_run.id))
                if v is not None:
                    warehouse = {
                        "is_within_capacity": v.is_within_capacity,
                        "total_pallet_required": float(v.total_pallet_required),
                        "total_pallet_capacity": float(v.total_pallet_capacity),
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
        }
