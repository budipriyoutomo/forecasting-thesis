"""
Warehouse endpoints (v3.0 Fase 6, redesain 24 Agustus 2026) — kapasitas gudang per
PRODUK & validasi, docs §5/§6.7.

GET    /warehouse/config                                → daftar konfigurasi (semua produk)
GET    /warehouse/config/{id}                            → satu baris
POST   /warehouse/config                                 → tambah (admin)
PUT    /warehouse/config/{id}                             → ubah kapasitas pallet/dus (admin)
DELETE /warehouse/config/{id}                             → hapus (admin)
GET    /forecast/runs/{run_id}/warehouse-validation       → validasi run (flag, non-blocking)

Router tanpa prefix — path lengkap (validasi berada di bawah /forecast/runs).
Semua logika lewat WarehouseService.
"""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.deps import CurrentUser, get_current_user, get_warehouse_service, require_role
from app.schemas.warehouse import (
    WarehouseConfigCreate,
    WarehouseConfigOut,
    WarehouseConfigUpdate,
    WarehouseValidationOut,
)
from app.services.warehouse_service import CapacityInput, WarehouseService, capacity_dus_of

router = APIRouter(tags=["warehouse"])


def _config_out(config) -> dict:
    return WarehouseConfigOut.model_validate(
        {
            "id": str(config.id),
            "product_id": str(config.product_id),
            "capacity_mode": config.capacity_mode,
            "pallet_qty": config.pallet_qty,
            "dus_qty": config.dus_qty,
            "dus_per_pallet": config.dus_per_pallet,
            "pcs_per_dus": config.pcs_per_dus,
            "capacity_dus": round(capacity_dus_of(config), 4),
            "capacity_qty": config.capacity_qty,
            "uom": config.uom,
        }
    ).model_dump(mode="json")


def _capacity_input(payload) -> CapacityInput:
    return CapacityInput(
        capacity_mode=payload.capacity_mode,
        pallet_qty=payload.pallet_qty,
        dus_qty=payload.dus_qty,
        dus_per_pallet=payload.dus_per_pallet,
        pcs_per_dus=payload.pcs_per_dus,
    )


@router.get("/warehouse/config", dependencies=[Depends(get_current_user)])
async def list_warehouse_config(service: WarehouseService = Depends(get_warehouse_service)):
    configs = await service.list_configs()
    return {"success": True, "data": [_config_out(c) for c in configs]}


@router.get("/warehouse/config/{config_id}", dependencies=[Depends(get_current_user)])
async def get_warehouse_config(
    config_id: str, service: WarehouseService = Depends(get_warehouse_service)
):
    config = await service.get_config(config_id)
    return {"success": True, "data": _config_out(config)}


@router.post("/warehouse/config", dependencies=[Depends(require_role("admin"))])
async def create_warehouse_config(
    payload: WarehouseConfigCreate, service: WarehouseService = Depends(get_warehouse_service)
):
    config = await service.create_config(payload.product_id, _capacity_input(payload))
    return JSONResponse(status_code=201, content={"success": True, "data": _config_out(config)})


@router.put("/warehouse/config/{config_id}", dependencies=[Depends(require_role("admin"))])
async def update_warehouse_config(
    config_id: str,
    payload: WarehouseConfigUpdate,
    service: WarehouseService = Depends(get_warehouse_service),
):
    config = await service.update_config(config_id, _capacity_input(payload))
    return {"success": True, "data": _config_out(config)}


@router.delete("/warehouse/config/{config_id}", dependencies=[Depends(require_role("admin"))])
async def delete_warehouse_config(
    config_id: str, service: WarehouseService = Depends(get_warehouse_service)
):
    await service.delete_config(config_id)
    return {"success": True, "data": {"id": config_id, "deleted": True}}


@router.get("/forecast/runs/{run_id}/warehouse-validation")
async def validate_run_capacity(
    run_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    service: WarehouseService = Depends(get_warehouse_service),
):
    v = await service.validate_for_run(current_user.user_id, run_id)
    return {
        "success": True,
        "data": WarehouseValidationOut(
            run_id=str(v.run_id),
            is_within_capacity=v.is_within_capacity,
            details=v.details,
        ).model_dump(mode="json"),
    }
