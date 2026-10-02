"""
Cost template endpoints (Fase 10, 2 Oktober 2026) — docs/ARCHITECTURE.md §5/§6.8.

GET    /cost-templates                 → daftar template
GET    /cost-templates/active          → template aktif (404 bila belum ada)
GET    /cost-templates/{id}            → detail + items
GET    /cost-templates/{id}/summary    → Σ depresiasi/overhead per bulan & saran H
POST   /cost-templates                 → buat (admin), tidak otomatis aktif
PUT    /cost-templates/{id}            → ganti penuh termasuk items (admin)
POST   /cost-templates/{id}/activate   → jadikan satu-satunya aktif (admin)
DELETE /cost-templates/{id}            → hapus (admin); bila aktif → EOQ kembali ke env

RBAC: baca semua role terautentikasi, tulis admin. Logika lewat CostTemplateService.
"""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.deps import get_cost_template_service, get_current_user, require_role
from app.schemas.cost_template import (
    CostTemplateCreate,
    CostTemplateItemOut,
    CostTemplateOut,
    CostTemplateSummaryOut,
    CostTemplateUpdate,
)
from app.services.cost_template_service import CostTemplateService, item_monthly_cost

router = APIRouter(prefix="/cost-templates", tags=["cost-templates"])


def _to_response(template) -> dict:
    return CostTemplateOut(
        id=str(template.id),
        name=template.name,
        description=template.description,
        ordering_cost=template.ordering_cost,
        holding_cost=template.holding_cost,
        is_active=bool(template.is_active),
        items=[
            CostTemplateItemOut(
                id=str(i.id) if getattr(i, "id", None) else None,
                item_type=i.item_type,
                name=i.name,
                monthly_amount=i.monthly_amount,
                purchase_price=i.purchase_price,
                salvage_value=i.salvage_value,
                useful_life_months=i.useful_life_months,
                qty=i.qty,
                monthly_cost=item_monthly_cost(i),
            )
            for i in template.items
        ],
    ).model_dump(mode="json")


@router.get("", dependencies=[Depends(get_current_user)])
async def list_cost_templates(service: CostTemplateService = Depends(get_cost_template_service)):
    templates = await service.list()
    return {"success": True, "data": [_to_response(t) for t in templates]}


# Didaftarkan sebelum /{template_id} supaya "active" tidak tertangkap sebagai id.
@router.get("/active", dependencies=[Depends(get_current_user)])
async def get_active_cost_template(service: CostTemplateService = Depends(get_cost_template_service)):
    return {"success": True, "data": _to_response(await service.get_active())}


@router.get("/{template_id}", dependencies=[Depends(get_current_user)])
async def get_cost_template(
    template_id: str, service: CostTemplateService = Depends(get_cost_template_service)
):
    return {"success": True, "data": _to_response(await service.get(template_id))}


@router.get("/{template_id}/summary", dependencies=[Depends(get_current_user)])
async def get_cost_template_summary(
    template_id: str, service: CostTemplateService = Depends(get_cost_template_service)
):
    template = await service.get(template_id)
    s = await service.summary(template_id)
    return {
        "success": True,
        "data": CostTemplateSummaryOut(
            template_id=str(template.id),
            total_depreciation_monthly=s.total_depreciation_monthly,
            total_overhead_monthly=s.total_overhead_monthly,
            total_monthly=s.total_monthly,
            total_capacity_dus=s.total_capacity_dus,
            suggested_holding_cost=s.suggested_holding_cost,
            holding_cost=template.holding_cost,
        ).model_dump(mode="json"),
    }


@router.post("", dependencies=[Depends(require_role("admin"))])
async def create_cost_template(
    payload: CostTemplateCreate, service: CostTemplateService = Depends(get_cost_template_service)
):
    template = await service.create(payload)
    return JSONResponse(status_code=201, content={"success": True, "data": _to_response(template)})


@router.put("/{template_id}", dependencies=[Depends(require_role("admin"))])
async def update_cost_template(
    template_id: str,
    payload: CostTemplateUpdate,
    service: CostTemplateService = Depends(get_cost_template_service),
):
    return {"success": True, "data": _to_response(await service.update(template_id, payload))}


@router.post("/{template_id}/activate", dependencies=[Depends(require_role("admin"))])
async def activate_cost_template(
    template_id: str, service: CostTemplateService = Depends(get_cost_template_service)
):
    return {"success": True, "data": _to_response(await service.activate(template_id))}


@router.delete("/{template_id}", dependencies=[Depends(require_role("admin"))])
async def delete_cost_template(
    template_id: str, service: CostTemplateService = Depends(get_cost_template_service)
):
    await service.delete(template_id)
    return {"success": True, "data": {"id": template_id, "deleted": True}}
