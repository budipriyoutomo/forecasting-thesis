"""
PlanningPipelineService (Fase 11.8, 30 Oktober 2026) — orkestrator alur sistem thesis
untuk satu forecast run (REVISI_V2 §1/§3.1, sheet "Diagra Alur Sistem"):

  [1] forecast produk (sudah ada di run)
  [2] MRP = forecast × BOM → safety stock, buffer stock, EOQ   (ReorderService)
  [3] proyeksi stok material & utilisasi gudang                (StockProjectionService)
  [4] evaluasi usulan inventory material + ringkasan biaya     (InventoryMetricsService, CostService)

Tiap tahap tetap service terpisah dengan endpoint sendiri; orkestrator hanya
mengurutkan & merangkum. Error di satu tahap menghentikan tahap berikutnya.
"""


class PlanningPipelineService:
    def __init__(self, reorder, projection, metrics, cost):
        self._reorder = reorder
        self._projection = projection
        self._metrics = metrics
        self._cost = cost

    async def run(self, user_id: str, run_id: str, current_stock: dict | None = None) -> dict:
        recs = await self._reorder.generate_for_run(user_id, run_id, current_stock)
        projection = await self._projection.generate_for_run(user_id, run_id)
        metrics = await self._metrics.compute_for_run(user_id, run_id)
        cost = await self._cost.get_cost_summary(user_id, run_id)

        proposed = [p for p in projection if p.scenario == "proposed"]
        return {
            "reorder": {
                "n_materials": len(recs),
                "n_urgent": sum(1 for r in recs if r.status == "urgent"),
                "n_missing_data": sum(1 for r in recs if (getattr(r, "item_status", None) or "COMPLETED") != "COMPLETED"),
            },
            "projection": {
                "n_rows": len(projection),
                "n_over_capacity": sum(1 for p in proposed if p.is_within_capacity is False),
                "n_shortage_periods": sum(1 for p in proposed if float(p.shortage_qty) > 0),
                "baseline_available": any(p.scenario == "baseline" for p in projection),
            },
            "evaluation": {
                "n_material_metrics": sum(1 for m in metrics if m.target_type == "material"),
                "n_product_metrics": sum(1 for m in metrics if m.target_type == "product"),
            },
            "cost": {
                "total_inventory_cost": _f(cost.total_inventory_cost),
                "baseline_inventory_cost": _f(cost.baseline_inventory_cost),
                "savings_pct": _f(cost.savings_pct),
                "shortage_cost": _f(getattr(cost, "shortage_cost", None)),
                "baseline_shortage_cost": _f(getattr(cost, "baseline_shortage_cost", None)),
                "eoq_method": getattr(cost, "eoq_method", None),
            },
        }


def _f(value):
    return float(value) if value is not None else None
