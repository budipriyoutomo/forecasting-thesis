"""
Endpoint reorder — /api/v1/reorder (Fase 5), docs/ARCHITECTURE.md §4/§5.

POST /reorder/recommendations  → generate + persist untuk satu run.
GET  /reorder/recommendations  → list (filter status: urgent/safe/overstock).

Semua perhitungan lewat ReorderService (fungsi murni compute_reorder), tidak inline.
"""
from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.api.deps import (
    CurrentUser,
    get_current_user,
    get_export_service,
    get_reorder_service,
)
from app.schemas.reorder import ReorderGenerateRequest, ReorderRecommendationOut
from app.services.export_service import ExportService
from app.services.reorder_service import ReorderService

router = APIRouter(prefix="/reorder", tags=["reorder"])


def _out(rec) -> dict:
    return ReorderRecommendationOut(
        material_id=str(rec.material_id),
        safety_stock=rec.safety_stock,
        reorder_point=rec.reorder_point,
        recommended_order_qty=rec.recommended_order_qty,
        status=rec.status,
        buffer_stock=getattr(rec, "buffer_stock", None),
        eoq_qty=getattr(rec, "eoq_qty", None),
        ordering_cost=getattr(rec, "ordering_cost", None),
        holding_cost=getattr(rec, "holding_cost", None),
        total_inventory_cost=getattr(rec, "total_inventory_cost", None),
    ).model_dump(mode="json")


@router.post("/recommendations", status_code=201)
async def generate_recommendations(
    payload: ReorderGenerateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: ReorderService = Depends(get_reorder_service),
):
    recs = await service.generate_for_run(current_user.user_id, payload.run_id, payload.current_stock)
    return {"success": True, "data": [_out(r) for r in recs], "message": "Rekomendasi reorder dibuat"}


@router.get("/recommendations/export")
async def export_recommendations(
    run_id: str = Query(...),
    format: Literal["xlsx", "pdf"] = Query(default="xlsx"),
    current_user: CurrentUser = Depends(get_current_user),
    service: ExportService = Depends(get_export_service),
):
    content, filename, mime = await service.export_reorder(current_user.user_id, run_id, format)
    return Response(
        content=content,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/recommendations")
async def list_recommendations(
    run_id: str = Query(...),
    status: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    service: ReorderService = Depends(get_reorder_service),
):
    recs = await service.list_for_run(current_user.user_id, run_id, status)
    return {"success": True, "data": [_out(r) for r in recs]}
