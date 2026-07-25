"""
BOMs endpoints (Fase 2 v3.0) — Bill of Materials, docs/ARCHITECTURE.md §5.

RBAC: baca semua role terautentikasi; tulis hanya `admin`. Logika lewat BomService.
`GET /boms?product_id=...` memfilter per produk.
"""
from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import JSONResponse

from app.api.deps import get_bom_service, get_current_user, require_role
from app.schemas.bom import BomCreate, BomResponse, BomUpdate
from app.services.bom_service import BomService

router = APIRouter(prefix="/boms", tags=["boms"])


def _to_response(bom) -> dict:
    return BomResponse.model_validate(
        {
            "id": str(bom.id),
            "product_id": str(bom.product_id),
            "material_id": str(bom.material_id),
            "qty_per_unit": bom.qty_per_unit,
        }
    ).model_dump(mode="json")


@router.get("", dependencies=[Depends(get_current_user)])
async def list_boms(product_id: str | None = None, service: BomService = Depends(get_bom_service)):
    boms = await service.list(product_id)
    return {"success": True, "data": [_to_response(b) for b in boms]}


@router.get("/{bom_id}", dependencies=[Depends(get_current_user)])
async def get_bom(bom_id: str, service: BomService = Depends(get_bom_service)):
    bom = await service.get(bom_id)
    return {"success": True, "data": _to_response(bom)}


@router.post("", dependencies=[Depends(require_role("admin"))])
async def create_bom(payload: BomCreate, service: BomService = Depends(get_bom_service)):
    bom = await service.create(payload)
    return JSONResponse(status_code=201, content={"success": True, "data": _to_response(bom)})


@router.put("/{bom_id}", dependencies=[Depends(require_role("admin"))])
async def update_bom(bom_id: str, payload: BomUpdate, service: BomService = Depends(get_bom_service)):
    bom = await service.update(bom_id, payload)
    return {"success": True, "data": _to_response(bom)}


@router.delete("/{bom_id}", dependencies=[Depends(require_role("admin"))])
async def delete_bom(bom_id: str, service: BomService = Depends(get_bom_service)):
    await service.delete(bom_id)
    return {"success": True, "data": {"id": bom_id, "deleted": True}}


@router.post("/import", dependencies=[Depends(require_role("admin"))])
async def import_boms(file: UploadFile, service: BomService = Depends(get_bom_service)):
    content = await file.read()
    result = await service.import_csv(content)
    return {"success": True, "data": result}
