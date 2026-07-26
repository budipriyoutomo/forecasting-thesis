"""Fase 2 v3.0 — endpoint /api/v1/boms. RBAC: tulis hanya admin."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import jwt
import pytest

from app.api.deps import get_bom_service
from app.config import get_settings
from app.main import app
from app.services.bom_service import BomService
from tests.unit.test_bom_service import FakeBom, FakeBomRepository
from tests.unit.test_material_service import FakeMaterial, FakeMaterialRepository
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


def _override(boms=None):
    app.dependency_overrides[get_bom_service] = lambda: BomService(
        repo=FakeBomRepository(boms or []),
        products=FakeProductRepository([FakeProduct(id="p1", code="P1", name="P", unit="PCS")]),
        materials=FakeMaterialRepository([FakeMaterial(id="m1", code="M1", name="M", unit="kg")]),
        model_factory=FakeBom,
    )


@pytest.fixture(autouse=True)
def _clear():
    yield
    app.dependency_overrides.pop(get_bom_service, None)


@pytest.mark.asyncio
async def test_create_bom_admin_201(client):
    _override([])
    body = {"product_id": "p1", "material_id": "m1", "qty_per_unit": 2.5}
    res = await client.post("/api/v1/boms", headers=_headers("admin"), json=body)
    assert res.status_code == 201
    assert res.json()["data"]["product_id"] == "p1"


@pytest.mark.asyncio
async def test_create_bom_non_admin_403(client):
    _override([])
    body = {"product_id": "p1", "material_id": "m1", "qty_per_unit": 1}
    res = await client.post("/api/v1/boms", headers=_headers("ppic"), json=body)
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_create_bom_produk_tak_ada_404(client):
    _override([])
    body = {"product_id": "nope", "material_id": "m1", "qty_per_unit": 1}
    res = await client.post("/api/v1/boms", headers=_headers("admin"), json=body)
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "PRODUCT_NOT_FOUND"


@pytest.mark.asyncio
async def test_list_bom_filter_product(client):
    _override([
        FakeBom(id="b1", product_id="p1", material_id="m1"),
        FakeBom(id="b2", product_id="p2", material_id="m1"),
    ])
    res = await client.get("/api/v1/boms?product_id=p1", headers=_headers("viewer"))
    assert res.status_code == 200
    data = res.json()["data"]
    assert {b["id"] for b in data} == {"b1"}


@pytest.mark.asyncio
async def test_get_bom_by_id(client):
    _override([FakeBom(id="b1", product_id="p1", material_id="m1", qty_per_unit=Decimal("2"))])
    res = await client.get("/api/v1/boms/b1", headers=_headers("viewer"))
    assert res.status_code == 200
    assert res.json()["data"]["id"] == "b1"


@pytest.mark.asyncio
async def test_update_bom_admin(client):
    _override([FakeBom(id="b1", product_id="p1", material_id="m1", qty_per_unit=Decimal("2"))])
    res = await client.put(
        "/api/v1/boms/b1", headers=_headers("admin"), json={"qty_per_unit": 5}
    )
    assert res.status_code == 200
    assert float(res.json()["data"]["qty_per_unit"]) == 5


@pytest.mark.asyncio
async def test_delete_bom_admin(client):
    _override([FakeBom(id="b1", product_id="p1", material_id="m1")])
    res = await client.delete("/api/v1/boms/b1", headers=_headers("admin"))
    assert res.status_code == 200
    assert res.json()["data"]["deleted"] is True


@pytest.mark.asyncio
async def test_import_boms_admin(client):
    _override([])
    csv = b"product_code,material_code,qty_per_unit\nP1,M1,3\n"
    res = await client.post(
        "/api/v1/boms/import",
        headers=_headers("admin"),
        files={"file": ("boms.csv", csv, "text/csv")},
    )
    assert res.status_code == 200
    assert res.json()["data"]["imported"] == 1
