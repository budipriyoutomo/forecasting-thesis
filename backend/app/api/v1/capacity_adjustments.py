"""
Endpoint adjust kapasitas gudang (Fase 11.17, 19 Nov 2026) — loop tahap 3 → tahap 2.

POST /forecast/runs/{run_id}/capacity-adjustments/suggest → usulan adjust SS & Buffer
     (simulasi ulang tahap 2→3, TIDAK disimpan; status within_capacity | adjusted | infeasible)
GET  /forecast/runs/{run_id}/capacity-adjustments          → adjust berlaku + riwayat (append-only)
POST /forecast/runs/{run_id}/capacity-adjustments          → simpan usulan / angka custom planner
POST /forecast/runs/{run_id}/capacity-adjustments/reset    → kembali ke nilai sistem
Setelah simpan/reset, klien menjalankan POST /forecast/runs/{run_id}/plan lagi.
"""
from fastapi import APIRouter, Body, Depends

from app.api.deps import CurrentUser, get_capacity_adjustment_service, get_current_user
from app.schemas.capacity_adjustment import (
    CapacityAdjustmentCreateRequest,
    CapacityAdjustmentOut,
    CapacityAdjustmentResetRequest,
)
from app.services.capacity_adjustment_service import CapacityAdjustmentService

router = APIRouter(prefix="/forecast/runs", tags=["capacity-adjustments"])


def _num(value):
    return float(value) if value is not None else None


def _out(row) -> dict:
    created = getattr(row, "created_at", None)
    return CapacityAdjustmentOut(
        id=str(row.id), run_id=str(row.run_id), material_id=str(row.material_id), user_id=str(row.user_id),
        source=row.source, service_level_pct=_num(row.service_level_pct), safety_stock=_num(row.safety_stock),
        buffer_stock=_num(row.buffer_stock), previous_value=row.previous_value, reason=row.reason,
        created_at=created.isoformat() if created else None,
    ).model_dump()


@router.post("/{run_id}/capacity-adjustments/suggest")
async def suggest_capacity_adjustment(
    run_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    service: CapacityAdjustmentService = Depends(get_capacity_adjustment_service),
):
    data = await service.suggest(current_user.user_id, run_id)
    return {"success": True, "data": data}


@router.get("/{run_id}/capacity-adjustments")
async def list_capacity_adjustments(
    run_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    service: CapacityAdjustmentService = Depends(get_capacity_adjustment_service),
):
    active = await service.list_active(current_user.user_id, run_id)
    history = await service.history(current_user.user_id, run_id)
    return {"success": True, "data": {"active": [_out(r) for r in active], "history": [_out(r) for r in history]}}


@router.post("/{run_id}/capacity-adjustments", status_code=201)
async def save_capacity_adjustments(
    run_id: str,
    payload: CapacityAdjustmentCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: CapacityAdjustmentService = Depends(get_capacity_adjustment_service),
):
    rows = await service.save(
        current_user.user_id, run_id, payload.source, [i.model_dump() for i in payload.items], payload.reason
    )
    return {"success": True, "data": [_out(r) for r in rows], "message": "Adjust kapasitas tersimpan"}


@router.post("/{run_id}/capacity-adjustments/reset")
async def reset_capacity_adjustments(
    run_id: str,
    payload: CapacityAdjustmentResetRequest | None = Body(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    service: CapacityAdjustmentService = Depends(get_capacity_adjustment_service),
):
    n = await service.reset(current_user.user_id, run_id, payload.reason if payload else None)
    return {"success": True, "data": {"n_reset": n}, "message": "Kembali ke nilai sistem"}
