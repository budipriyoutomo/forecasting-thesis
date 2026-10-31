"""
Endpoint Fase 7 v3.0 — total biaya & evaluasi kinerja inventory, docs §5/§6.8.

GET /forecast/runs/{run_id}/cost-summary        → TIC usulan vs baseline + % penghematan
GET /forecast/runs/{run_id}/inventory-metrics   → service level, fill rate, stock out, turnover
GET /forecast/runs/{run_id}/inventory-metrics/export → unduh metrik tersimpan (xlsx|pdf)

Router tanpa prefix (path lengkap di bawah /forecast/runs). Keduanya GET: dihitung
dari data run tersimpan tanpa input request-time (larangan #18 tak berlaku).
Semua logika lewat CostService / InventoryMetricsService.
"""
from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.api.deps import (
    CurrentUser,
    get_cost_service,
    get_current_user,
    get_export_service,
    get_inventory_metrics_service,
)
from app.services.export_service import ExportService
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
            purchase_cost=summary.purchase_cost,
            n_materials_without_price=summary.n_materials_without_price,
            cost_source=summary.cost_source,
            cost_template_name=summary.cost_template_name,
            eoq_method=summary.eoq_method,
            shortage_cost=summary.shortage_cost,
            baseline_shortage_cost=summary.baseline_shortage_cost,
            savings_pct=summary.savings_pct,
        ).model_dump(mode="json"),
    }


@router.get("/forecast/runs/{run_id}/inventory-metrics")
async def inventory_metrics(
    run_id: str,
    target_type: str | None = None,
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
                inventory_days=getattr(r, "inventory_days", None),
                shortage_cost=getattr(r, "shortage_cost", None),
            ).model_dump(mode="json")
            for r in rows
            if target_type is None or r.target_type == target_type
        ],
    }


@router.get("/forecast/runs/{run_id}/inventory-metrics/export")
async def export_inventory_metrics(
    run_id: str,
    format: Literal["xlsx", "pdf"] = Query(default="xlsx"),
    target_type: Literal["product", "material"] | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    service: ExportService = Depends(get_export_service),
):
    content, filename, mime = await service.export_metrics(current_user.user_id, run_id, format, target_type)
    return Response(
        content=content,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
