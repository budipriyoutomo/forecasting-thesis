"""Fase 2 v3.0 — endpoint /api/v1/products. RBAC: tulis hanya admin."""
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.api.deps import get_product_service
from app.config import get_settings
from app.main import app
from app.services.product_service import ProductService
from tests.unit.test_product_service import FakeProduct, FakeProductRepository

settings = get_settings()


def _headers(role: str) -> dict:
    payload = {
        "sub": "00000000-0000-0000-0000-000000000009",
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


def _override(products=None):
    app.dependency_overrides[get_product_service] = lambda: ProductService(
        FakeProductRepository(products or []), model_factory=FakeProduct
    )


@pytest.fixture(autouse=True)
def _clear():
    yield
    app.dependency_overrides.pop(get_product_service, None)


@pytest.mark.asyncio
async def test_list_products(client):
    _override([FakeProduct(id="p1", code="KBYPL 200", name="KIN Yogurt", unit="PCS")])
    res = await client.get("/api/v1/products", headers=_headers("viewer"))
    assert res.status_code == 200
    assert res.json()["data"][0]["code"] == "KBYPL 200"


@pytest.mark.asyncio
async def test_list_tanpa_token_401(client):
    _override([])
    res = await client.get("/api/v1/products")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_create_product_admin_201(client):
    _override([])
    body = {"code": "KBYPL 700", "name": "KIN Yogurt 700ml", "unit": "PCS"}
    res = await client.post("/api/v1/products", headers=_headers("admin"), json=body)
    assert res.status_code == 201
    assert res.json()["data"]["code"] == "KBYPL 700"


@pytest.mark.asyncio
async def test_create_product_non_admin_403(client):
    _override([])
    body = {"code": "X", "name": "X", "unit": "PCS"}
    res = await client.post("/api/v1/products", headers=_headers("ppic"), json=body)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "AUTH_FORBIDDEN"


@pytest.mark.asyncio
async def test_create_duplikat_409(client):
    _override([FakeProduct(id="p1", code="DUP", name="A", unit="PCS")])
    res = await client.post(
        "/api/v1/products", headers=_headers("admin"), json={"code": "DUP", "name": "B", "unit": "PCS"}
    )
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "PRODUCT_CODE_EXISTS"


@pytest.mark.asyncio
async def test_get_product_tidak_ada_404(client):
    _override([])
    res = await client.get("/api/v1/products/nope", headers=_headers("viewer"))
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "PRODUCT_NOT_FOUND"


@pytest.mark.asyncio
async def test_update_product_admin(client):
    _override([FakeProduct(id="p1", code="KBYPL 200", name="Lama", unit="PCS")])
    res = await client.put(
        "/api/v1/products/p1", headers=_headers("admin"), json={"name": "Baru"}
    )
    assert res.status_code == 200
    assert res.json()["data"]["name"] == "Baru"


@pytest.mark.asyncio
async def test_delete_product_admin(client):
    _override([FakeProduct(id="p1", code="KBYPL 200", name="X", unit="PCS")])
    res = await client.delete("/api/v1/products/p1", headers=_headers("admin"))
    assert res.status_code == 200
    assert res.json()["data"]["deleted"] is True


@pytest.mark.asyncio
async def test_import_products_admin(client):
    _override([])
    csv = b"code,name,unit\nKBYPL 200,KIN Yogurt 200ml,PCS\nKBYPL 700,KIN Yogurt 700ml,PCS\n"
    res = await client.post(
        "/api/v1/products/import",
        headers=_headers("admin"),
        files={"file": ("products.csv", csv, "text/csv")},
    )
    assert res.status_code == 200
    assert res.json()["data"]["imported"] == 2
