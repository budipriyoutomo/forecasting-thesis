"""
Stock projection endpoints (Fase 11.6, 30 Oktober 2026) — tahap 3 thesis (REVISI_V2 §5.1).

POST /forecast/runs/{run_id}/stock-projection → hitung ulang proyeksi (usulan & baseline)
GET  /forecast/runs/{run_id}/stock-projection → baca (?scenario=proposed|baseline)
GET  /forecast/runs/{run_id}/stock-projection/export → unduh xlsx|pdf (?format, ?scenario)
Kapasitas terlampaui = flag `is_within_capacity`, bukan error (larangan #17).
"""
from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.api.deps import CurrentUser, get_current_user, get_export_service, get_stock_projection_service
from app.services.export_service import ExportService
from app.services.stock_projection_service import StockProjectionService

router = APIRouter(prefix="/forecast/runs", tags=["stock-projection"])


def _out(r) -> dict:
    return {
        "material_id": str(r.material_id),
        "scenario": r.scenario,
        "period": str(r.period),
        "opening_qty": r.opening_qty,
        "receipt_qty": r.receipt_qty,
        "usage_qty": r.usage_qty,
        "order_qty": r.order_qty,
        "ending_qty": r.ending_qty,
        "shortage_qty": r.shortage_qty,
        "capacity_qty": r.capacity_qty,
        "utilization_opening_pct": r.utilization_opening_pct,
        "utilization_ending_pct": r.utilization_ending_pct,
        "is_within_capacity": r.is_within_capacity,
    }


@router.post("/{run_id}/stock-projection")
async def generate_stock_projection(
    run_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    service: StockProjectionService = Depends(get_stock_projection_service),
):
    rows = await service.generate_for_run(current_user.user_id, run_id)
    return {"success": True, "data": [_out(r) for r in rows], "message": "Proyeksi stok dihitung"}


@router.get("/{run_id}/stock-projection")
async def get_stock_projection(
    run_id: str,
    scenario: str | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    service: StockProjectionService = Depends(get_stock_projection_service),
):
    rows = await service.list_for_run(current_user.user_id, run_id, scenario)
    return {"success": True, "data": [_out(r) for r in rows]}


@router.get("/{run_id}/stock-projection/export")
async def export_stock_projection(
    run_id: str,
    format: Literal["xlsx", "pdf"] = Query(default="xlsx"),
    scenario: Literal["proposed", "baseline"] | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    service: ExportService = Depends(get_export_service),
):
    content, filename, mime = await service.export_stock_projection(current_user.user_id, run_id, format, scenario)
    return Response(
        content=content,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
