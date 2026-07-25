"""
Warehouse endpoints (v3.0 Fase 6) — kapasitas gudang & validasi, docs §5/§6.7.

GET  /warehouse/config                                  → konfigurasi gudang
PUT  /warehouse/config                                  → set/ubah (admin)
GET  /forecast/runs/{run_id}/warehouse-validation       → validasi run (flag, non-blocking)

Router tanpa prefix — path lengkap (validasi berada di bawah /forecast/runs).
Semua logika lewat WarehouseService.
"""
from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, get_current_user, get_warehouse_service, require_role
from app.schemas.warehouse import WarehouseConfigInput, WarehouseConfigOut, WarehouseValidationOut
from app.services.warehouse_service import WarehouseService

router = APIRouter(tags=["warehouse"])


def _config_out(config) -> dict:
    return WarehouseConfigOut.model_validate(
        {
            "category": config.category,
            "warehouse_area_m2": config.warehouse_area_m2,
            "pallet_dimension": config.pallet_dimension,
        }
    ).model_dump(mode="json")


@router.get("/warehouse/config", dependencies=[Depends(get_current_user)])
async def get_warehouse_config(
    category: str = "packaging", service: WarehouseService = Depends(get_warehouse_service)
):
    config = await service.get_config(category)
    return {"success": True, "data": _config_out(config)}


@router.put("/warehouse/config", dependencies=[Depends(require_role("admin"))])
async def set_warehouse_config(
    payload: WarehouseConfigInput, service: WarehouseService = Depends(get_warehouse_service)
):
    config = await service.upsert_config(
        payload.category, payload.warehouse_area_m2, payload.pallet_dimension.model_dump()
    )
    return {"success": True, "data": _config_out(config)}


@router.get("/forecast/runs/{run_id}/warehouse-validation")
async def validate_run_capacity(
    run_id: str,
    category: str = "packaging",
    current_user: CurrentUser = Depends(get_current_user),
    service: WarehouseService = Depends(get_warehouse_service),
):
    v = await service.validate_for_run(current_user.user_id, run_id, category)
    return {
        "success": True,
        "data": WarehouseValidationOut(
            run_id=str(v.run_id),
            total_pallet_capacity=v.total_pallet_capacity,
            total_pallet_required=v.total_pallet_required,
            is_within_capacity=v.is_within_capacity,
        ).model_dump(mode="json"),
    }
