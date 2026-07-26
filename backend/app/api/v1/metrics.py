"""
Endpoint Fase 7 v3.0 — total biaya & evaluasi kinerja inventory, docs §5/§6.8.

GET /forecast/runs/{run_id}/cost-summary        → TIC usulan vs baseline + % penghematan
GET /forecast/runs/{run_id}/inventory-metrics   → service level, fill rate, stock out, turnover

Router tanpa prefix (path lengkap di bawah /forecast/runs). Keduanya GET: dihitung
dari data run tersimpan tanpa input request-time (larangan #18 tak berlaku).
Semua logika lewat CostService / InventoryMetricsService.
"""
from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, get_cost_service, get_current_user, get_inventory_metrics_service
from app.schemas.metrics import CostSummaryOut, InventoryMetricOut
from app.services.cost_service import CostService
from app.services.inventory_metrics_service import InventoryMetricsService

router = APIRouter(tags=["metrics"])


@router.get("/forecast/runs/{run_id}/cost-summary")
async def cost_summary(
    run_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    service: CostService = Depends(get_cost_service),
):
    summary = await service.get_cost_summary(current_user.user_id, run_id)
    return {
        "success": True,
        "data": CostSummaryOut(
            run_id=str(run_id),
            total_ordering_cost=summary.total_ordering_cost,
            total_holding_cost=summary.total_holding_cost,
            total_inventory_cost=summary.total_inventory_cost,
            baseline_inventory_cost=summary.baseline_inventory_cost,
            savings_pct=summary.savings_pct,
        ).model_dump(mode="json"),
    }


@router.get("/forecast/runs/{run_id}/inventory-metrics")
async def inventory_metrics(
    run_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    service: InventoryMetricsService = Depends(get_inventory_metrics_service),
):
    rows = await service.compute_for_run(current_user.user_id, run_id)
    return {
        "success": True,
        "data": [
            InventoryMetricOut(
                target_type=r.target_type,
                target_id=str(r.target_id),
                scope=r.scope,
                service_level=r.service_level,
                fill_rate=r.fill_rate,
                stock_out_rate=r.stock_out_rate,
                inventory_turnover=r.inventory_turnover,
            ).model_dump(mode="json")
            for r in rows
        ],
    }
