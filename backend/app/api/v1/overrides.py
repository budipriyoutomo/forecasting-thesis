"""
Endpoint overrides — /api/v1/overrides (Fase 6), docs/ARCHITECTURE.md §5.

POST /overrides            → buat override baru (append-only, reason wajib).
GET  /overrides?target_id= → audit trail satu target.
GET  /overrides/reorder?run_id=&material_id= → riwayat override reorder satu material dalam
     satu run (v3.3) — tetap lengkap setelah rekomendasi di-generate ulang (id baru).
"""
from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUser, get_current_user, get_override_service
from app.schemas.override import OverrideCreateRequest, OverrideOut
from app.services.override_service import OverrideService

router = APIRouter(prefix="/overrides", tags=["overrides"])


def _out(ov) -> dict:
    return OverrideOut(
        id=str(ov.id),
        target_type=ov.target_type,
        target_id=str(ov.target_id),
        user_id=str(ov.user_id),
        previous_value=ov.previous_value,
        new_value=ov.new_value,
        reason=ov.reason,
        created_at=ov.created_at.isoformat() if getattr(ov, "created_at", None) else None,
        run_id=str(ov.run_id) if getattr(ov, "run_id", None) else None,
        material_id=str(ov.material_id) if getattr(ov, "material_id", None) else None,
    ).model_dump()


@router.post("", status_code=201)
async def create_override(
    payload: OverrideCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: OverrideService = Depends(get_override_service),
):
    ov = await service.create(
        current_user.user_id, payload.target_type, payload.target_id, payload.new_value, payload.reason
    )
    return {"success": True, "data": _out(ov), "message": "Override tersimpan"}


@router.get("")
async def list_overrides(
    target_id: str = Query(...),
    current_user: CurrentUser = Depends(get_current_user),
    service: OverrideService = Depends(get_override_service),
):
    trail = await service.list_for_target(target_id)
    return {"success": True, "data": [_out(o) for o in trail]}


@router.get("/reorder")
async def list_reorder_overrides(
    run_id: str = Query(...),
    material_id: str = Query(...),
    current_user: CurrentUser = Depends(get_current_user),
    service: OverrideService = Depends(get_override_service),
):
    trail = await service.list_for_reorder(run_id, material_id)
    return {"success": True, "data": [_out(o) for o in trail]}
