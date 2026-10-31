"""
Material component endpoints (Fase 11.3, 30 Oktober 2026) — BOM multi-level, REVISI_V2 §3.4.

GET    /materials/{id}/components   → komponen level berikutnya
POST   /materials/{id}/components   → tambah (admin); siklus → 422 BOM_CYCLE_DETECTED
DELETE /material-components/{id}    → hapus (admin)
GET    /boms/tree?product_id=       → tree FG → material → komponen
"""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.api.deps import get_current_user, get_material_component_service, require_role
from app.services.material_component_service import MaterialComponentService

router = APIRouter(tags=["material-components"])


class MaterialComponentCreate(BaseModel):
    component_material_id: str
    qty_per_unit: float = Field(gt=0)


def _out(row) -> dict:
    return {
        "id": str(row.id),
        "parent_material_id": str(row.parent_material_id),
        "component_material_id": str(row.component_material_id),
        "qty_per_unit": float(row.qty_per_unit),
    }


@router.get("/materials/{material_id}/components", dependencies=[Depends(get_current_user)])
async def list_components(material_id: str, service: MaterialComponentService = Depends(get_material_component_service)):
    return {"success": True, "data": [_out(r) for r in await service.list(material_id)]}


@router.post("/materials/{material_id}/components", dependencies=[Depends(require_role("admin"))])
async def add_component(
    material_id: str,
    payload: MaterialComponentCreate,
    service: MaterialComponentService = Depends(get_material_component_service),
):
    row = await service.add(material_id, payload.component_material_id, payload.qty_per_unit)
    return JSONResponse(status_code=201, content={"success": True, "data": _out(row)})


@router.delete("/material-components/{component_id}", dependencies=[Depends(require_role("admin"))])
async def delete_component(component_id: str, service: MaterialComponentService = Depends(get_material_component_service)):
    await service.delete(component_id)
    return {"success": True, "data": {"id": component_id, "deleted": True}}


@router.get("/boms/tree", dependencies=[Depends(get_current_user)])
async def bom_tree(product_id: str, service: MaterialComponentService = Depends(get_material_component_service)):
    return {"success": True, "data": await service.tree(product_id)}
