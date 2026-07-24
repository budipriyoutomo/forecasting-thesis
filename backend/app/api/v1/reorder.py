"""
Endpoint reorder — /api/v1/reorder (Fase 5), docs/ARCHITECTURE.md §4/§5.

POST /reorder/recommendations  → generate + persist untuk satu run.
GET  /reorder/recommendations  → list (filter status: urgent/safe/overstock).

Semua perhitungan lewat ReorderService (fungsi murni compute_reorder), tidak inline.
"""
from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUser, get_current_user, get_reorder_service
from app.schemas.reorder import ReorderGenerateRequest, ReorderRecommendationOut
from app.services.reorder_service import ReorderService

router = APIRouter(prefix="/reorder", tags=["reorder"])


def _out(rec) -> dict:
    return ReorderRecommendationOut(
        material_id=str(rec.material_id),
        safety_stock=rec.safety_stock,
        reorder_point=rec.reorder_point,
        recommended_order_qty=rec.recommended_order_qty,
        status=rec.status,
    ).model_dump(mode="json")


@router.post("/recommendations", status_code=201)
async def generate_recommendations(
    payload: ReorderGenerateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: ReorderService = Depends(get_reorder_service),
):
    recs = await service.generate_for_run(current_user.user_id, payload.run_id, payload.current_stock)
    return {"success": True, "data": [_out(r) for r in recs], "message": "Rekomendasi reorder dibuat"}


@router.get("/recommendations")
async def list_recommendations(
    run_id: str = Query(...),
    status: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    service: ReorderService = Depends(get_reorder_service),
):
    recs = await service.list_for_run(current_user.user_id, run_id, status)
    return {"success": True, "data": [_out(r) for r in recs]}
