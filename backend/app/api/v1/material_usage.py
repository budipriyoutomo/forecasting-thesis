"""
Material usage endpoints (Fase 11.1, 30 Oktober 2026) — buffer stock (REVISI_V2 §3.8).

POST /material-usage/import        → upload pemakaian aktual CSV/XLSX (admin/ppic)
GET  /material-usage               → riwayat (opsional ?material_id=)
GET  /material-usage/waste-factors → Σ aktual ÷ Σ standar per material
"""
from fastapi import APIRouter, Depends, UploadFile

from app.api.deps import get_current_user, get_material_usage_service, require_role
from app.services.material_usage_service import MaterialUsageService

router = APIRouter(prefix="/material-usage", tags=["material-usage"])


def _f(v):
    return float(v) if v is not None else None


@router.post("/import", dependencies=[Depends(require_role("admin", "ppic"))])
async def import_material_usage(file: UploadFile, service: MaterialUsageService = Depends(get_material_usage_service)):
    result = await service.import_usage(file.filename or "", await file.read())
    return {"success": True, "data": result, "message": f"{result['imported']} baris pemakaian diimpor"}


@router.get("", dependencies=[Depends(get_current_user)])
async def list_material_usage(
    material_id: str | None = None, service: MaterialUsageService = Depends(get_material_usage_service)
):
    rows = await service.list(material_id)
    data = [
        {
            "material_id": str(r.material_id),
            "product_id": str(r.product_id) if r.product_id else None,
            "period": str(r.period),
            "production_output": _f(r.production_output),
            "standard_usage": _f(r.standard_usage),
            "actual_usage": _f(r.actual_usage),
        }
        for r in rows
    ]
    return {"success": True, "data": data}


@router.get("/waste-factors", dependencies=[Depends(get_current_user)])
async def list_waste_factors(service: MaterialUsageService = Depends(get_material_usage_service)):
    factors = await service.waste_factors()
    return {
        "success": True,
        "data": [{"material_id": mid, "waste_factor": f} for mid, f in sorted(factors.items())],
    }
