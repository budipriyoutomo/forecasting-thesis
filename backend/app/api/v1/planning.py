"""
Planning pipeline endpoint (Fase 11.8, 30 Oktober 2026) — REVISI_V2 §5.1.

POST /forecast/runs/{run_id}/plan → jalankan tahap 2→4 berurutan (reorder → proyeksi
stok → evaluasi → biaya). Body opsional `current_stock` = fallback bila belum ada
snapshot stok ERP (revisi keputusan #16). Hasil tiap tahap tetap dibaca lewat GET
endpoint masing-masing.
"""
from fastapi import APIRouter, Body, Depends

from app.api.deps import CurrentUser, get_current_user, get_planning_pipeline_service
from app.services.planning_pipeline_service import PlanningPipelineService

router = APIRouter(prefix="/forecast/runs", tags=["planning"])


@router.post("/{run_id}/plan")
async def run_planning_pipeline(
    run_id: str,
    current_stock: dict[str, float] | None = Body(default=None, embed=True),
    current_user: CurrentUser = Depends(get_current_user),
    service: PlanningPipelineService = Depends(get_planning_pipeline_service),
):
    summary = await service.run(current_user.user_id, run_id, current_stock)
    return {"success": True, "data": summary, "message": "Perencanaan persediaan selesai"}
