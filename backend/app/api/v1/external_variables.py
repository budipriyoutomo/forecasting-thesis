"""
External variable endpoints (Fase 11.2b, 30 Oktober 2026) — docs/ARCHITECTURE.md §5.

GET    /external-variables                 → daftar + jumlah nilai tersimpan
POST   /external-variables                 → buat (admin)
PUT    /external-variables/{id}            → ubah / toggle aktif (admin)
DELETE /external-variables/{id}            → hapus + seluruh nilainya (admin)
POST   /external-variables/values/import   → upload nilai per periode CSV/XLSX (admin)
GET    /external-variables/{id}/values     → nilai (opsional ?product_id=)
DELETE /external-variables/{id}/values     → hapus seluruh nilai (admin)

RBAC: baca semua role terautentikasi, tulis admin.
"""
from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import JSONResponse

from app.api.deps import get_current_user, get_external_variable_service, require_role
from app.schemas.external_variable import (
    ExternalVariableCreate,
    ExternalVariableOut,
    ExternalVariableUpdate,
    ExternalVariableValueOut,
)
from app.services.external_variable_service import ExternalVariableService

router = APIRouter(prefix="/external-variables", tags=["external-variables"])


def _to_response(var, n_values: int = 0) -> dict:
    return ExternalVariableOut(
        id=str(var.id),
        code=var.code,
        name=var.name,
        value_type=var.value_type,
        scope=var.scope,
        unit=var.unit,
        description=var.description,
        is_active=bool(var.is_active),
        n_values=n_values,
        created_at=getattr(var, "created_at", None),
        updated_at=getattr(var, "updated_at", None),
    ).model_dump(mode="json")


@router.get("", dependencies=[Depends(get_current_user)])
async def list_external_variables(service: ExternalVariableService = Depends(get_external_variable_service)):
    counts = await service.value_counts()
    return {"success": True, "data": [_to_response(v, counts.get(str(v.id), 0)) for v in await service.list()]}


@router.post("", dependencies=[Depends(require_role("admin"))])
async def create_external_variable(
    payload: ExternalVariableCreate, service: ExternalVariableService = Depends(get_external_variable_service)
):
    var = await service.create(payload)
    return JSONResponse(status_code=201, content={"success": True, "data": _to_response(var)})


# Didaftarkan sebelum /{variable_id} supaya "values" tidak tertangkap sebagai id.
@router.post("/values/import", dependencies=[Depends(require_role("admin"))])
async def import_external_variable_values(
    file: UploadFile, service: ExternalVariableService = Depends(get_external_variable_service)
):
    result = await service.import_values(file.filename or "", await file.read())
    return {"success": True, "data": result, "message": f"{result['imported']} nilai diimpor"}


@router.put("/{variable_id}", dependencies=[Depends(require_role("admin"))])
async def update_external_variable(
    variable_id: str,
    payload: ExternalVariableUpdate,
    service: ExternalVariableService = Depends(get_external_variable_service),
):
    return {"success": True, "data": _to_response(await service.update(variable_id, payload))}


@router.delete("/{variable_id}", dependencies=[Depends(require_role("admin"))])
async def delete_external_variable(
    variable_id: str, service: ExternalVariableService = Depends(get_external_variable_service)
):
    await service.delete(variable_id)
    return {"success": True, "data": {"id": variable_id, "deleted": True}}


@router.get("/{variable_id}/values", dependencies=[Depends(get_current_user)])
async def list_external_variable_values(
    variable_id: str,
    product_id: str | None = None,
    service: ExternalVariableService = Depends(get_external_variable_service),
):
    rows = await service.list_values(variable_id, product_id)
    data = [
        ExternalVariableValueOut(
            product_id=str(r.product_id) if r.product_id else None, period=r.period, value=float(r.value)
        ).model_dump(mode="json")
        for r in rows
    ]
    return {"success": True, "data": data}


@router.delete("/{variable_id}/values", dependencies=[Depends(require_role("admin"))])
async def clear_external_variable_values(
    variable_id: str, service: ExternalVariableService = Depends(get_external_variable_service)
):
    n = await service.clear_values(variable_id)
    return {"success": True, "data": {"id": variable_id, "deleted_values": n}}
