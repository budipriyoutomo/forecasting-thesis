"""
Products endpoints (Fase 2 v3.0) — master data produk jadi, docs/ARCHITECTURE.md §5.

RBAC (FR-8.2): baca semua role terautentikasi; tulis (create/update/delete/import)
hanya `admin`. Semua logika lewat ProductService, tidak inline.
"""
from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import JSONResponse

from app.api.deps import get_current_user, get_product_service, require_role
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["products"])


def _to_response(product) -> dict:
    return ProductResponse.model_validate(
        {
            "id": str(product.id),
            "code": product.code,
            "name": product.name,
            "category": product.category,
            "unit": product.unit,
        }
    ).model_dump(mode="json")


@router.get("", dependencies=[Depends(get_current_user)])
async def list_products(service: ProductService = Depends(get_product_service)):
    products = await service.list()
    return {"success": True, "data": [_to_response(p) for p in products]}


@router.get("/{product_id}", dependencies=[Depends(get_current_user)])
async def get_product(product_id: str, service: ProductService = Depends(get_product_service)):
    product = await service.get(product_id)
    return {"success": True, "data": _to_response(product)}


@router.post("", dependencies=[Depends(require_role("admin"))])
async def create_product(payload: ProductCreate, service: ProductService = Depends(get_product_service)):
    product = await service.create(payload)
    return JSONResponse(status_code=201, content={"success": True, "data": _to_response(product)})


@router.put("/{product_id}", dependencies=[Depends(require_role("admin"))])
async def update_product(
    product_id: str, payload: ProductUpdate, service: ProductService = Depends(get_product_service)
):
    product = await service.update(product_id, payload)
    return {"success": True, "data": _to_response(product)}


@router.delete("/{product_id}", dependencies=[Depends(require_role("admin"))])
async def delete_product(product_id: str, service: ProductService = Depends(get_product_service)):
    await service.delete(product_id)
    return {"success": True, "data": {"id": product_id, "deleted": True}}


@router.post("/import", dependencies=[Depends(require_role("admin"))])
async def import_products(file: UploadFile, service: ProductService = Depends(get_product_service)):
    content = await file.read()
    result = await service.import_csv(content)
    return {"success": True, "data": result}
