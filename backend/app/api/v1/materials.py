"""
Materials endpoints (Fase 2) — master data material, docs/ARCHITECTURE.md §5.

RBAC (FR-8.2): baca boleh semua role terautentikasi; tulis (create/update/delete/
import) hanya `admin`. Semua logika lewat MaterialService, tidak inline.
"""
from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import JSONResponse

from app.api.deps import get_current_user, get_material_service, require_role
from app.schemas.material import MaterialCreate, MaterialResponse, MaterialUpdate
from app.services.material_service import MaterialService

router = APIRouter(prefix="/materials", tags=["materials"])


def _to_response(material) -> dict:
    return MaterialResponse.model_validate(
        {
            "id": str(material.id),
            "code": material.code,
            "name": material.name,
            "category": material.category,
            "unit": material.unit,
            "lead_time_days": material.lead_time_days,
            "moq": material.moq,
            "manual_safety_stock": material.manual_safety_stock,
        }
    ).model_dump(mode="json")


@router.get("", dependencies=[Depends(get_current_user)])
async def list_materials(service: MaterialService = Depends(get_material_service)):
    materials = await service.list()
    return {"success": True, "data": [_to_response(m) for m in materials]}


@router.get("/{material_id}", dependencies=[Depends(get_current_user)])
async def get_material(material_id: str, service: MaterialService = Depends(get_material_service)):
    material = await service.get(material_id)
    return {"success": True, "data": _to_response(material)}


@router.post("", dependencies=[Depends(require_role("admin"))])
async def create_material(
    payload: MaterialCreate, service: MaterialService = Depends(get_material_service)
):
    material = await service.create(payload)
    return JSONResponse(status_code=201, content={"success": True, "data": _to_response(material)})


@router.put("/{material_id}", dependencies=[Depends(require_role("admin"))])
async def update_material(
    material_id: str, payload: MaterialUpdate, service: MaterialService = Depends(get_material_service)
):
    material = await service.update(material_id, payload)
    return {"success": True, "data": _to_response(material)}


@router.delete("/{material_id}", dependencies=[Depends(require_role("admin"))])
async def delete_material(material_id: str, service: MaterialService = Depends(get_material_service)):
    await service.delete(material_id)
    return {"success": True, "data": {"id": material_id, "deleted": True}}


@router.post("/import", dependencies=[Depends(require_role("admin"))])
async def import_materials(
    file: UploadFile, service: MaterialService = Depends(get_material_service)
):
    content = await file.read()
    result = await service.import_csv(content)
    return {"success": True, "data": result}
