"""
Fase 6 v3.0, redesain 24 Agustus 2026 — endpoint /warehouse/config (CRUD per
produk) & warehouse-validation. RBAC: POST/PUT/DELETE admin, GET semua role.
"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest

from app.api.deps import get_warehouse_service
from app.config import get_settings
from app.main import app
from app.services.warehouse_service import WarehouseService
from tests.unit.test_warehouse_service import (
    FakeConfigRepo,
    FakeForecastRepo,
    FakeProductRepo,
    FakeValidationRepo,
    _config,
    _result,
)

settings = get_settings()
USER_SUB = "00000000-0000-0000-0000-000000000009"


def _headers(role: str) -> dict:
    payload = {"sub": USER_SUB, "role": role, "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


def _override(run=None, results=None, configs=None, products=None):
    app.dependency_overrides[get_warehouse_service] = lambda: WarehouseService(
        config_repo=FakeConfigRepo(configs),
        validation_repo=FakeValidationRepo(),
        forecast_repo=FakeForecastRepo(run, results),
        products=FakeProductRepo(products if products is not None else ["p1", "p2"]),
    )


@pytest.fixture(autouse=True)
def _clear():
    yield
    app.dependency_overrides.pop(get_warehouse_service, None)


@pytest.mark.asyncio
async def test_list_config_kosong(client):
    _override()
    res = await client.get("/api/v1/warehouse/config", headers=_headers("viewer"))
    assert res.status_code == 200
    assert res.json()["data"] == []


@pytest.mark.asyncio
async def test_post_config_admin_lalu_list(client):
    _override()
    res = await client.post(
        "/api/v1/warehouse/config", headers=_headers("admin"), json={"product_id": "p1", "capacity_qty": 500}
    )
    assert res.status_code == 201
    assert float(res.json()["data"]["capacity_qty"]) == 500
    assert res.json()["data"]["product_id"] == "p1"


@pytest.mark.asyncio
async def test_post_config_non_admin_403(client):
    _override()
    res = await client.post(
        "/api/v1/warehouse/config", headers=_headers("ppic"), json={"product_id": "p1", "capacity_qty": 500}
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_post_config_produk_tidak_ada_404(client):
    _override(products=[])
    res = await client.post(
        "/api/v1/warehouse/config", headers=_headers("admin"), json={"product_id": "ghost", "capacity_qty": 500}
    )
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "PRODUCT_NOT_FOUND"


@pytest.mark.asyncio
async def test_post_config_duplikat_409(client):
    _override(configs=[_config(pid="p1")])
    res = await client.post(
        "/api/v1/warehouse/config", headers=_headers("admin"), json={"product_id": "p1", "capacity_qty": 500}
    )
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "WAREHOUSE_CONFIG_EXISTS"


@pytest.mark.asyncio
async def test_put_config_admin(client):
    _override(configs=[_config(cid="c1", pid="p1", capacity=100)])
    res = await client.put(
        "/api/v1/warehouse/config/c1", headers=_headers("admin"), json={"capacity_qty": 250}
    )
    assert res.status_code == 200
    assert float(res.json()["data"]["capacity_qty"]) == 250


@pytest.mark.asyncio
async def test_put_config_non_admin_403(client):
    _override(configs=[_config(cid="c1", pid="p1")])
    res = await client.put(
        "/api/v1/warehouse/config/c1", headers=_headers("ppic"), json={"capacity_qty": 250}
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_delete_config_admin(client):
    _override(configs=[_config(cid="c1", pid="p1")])
    res = await client.delete("/api/v1/warehouse/config/c1", headers=_headers("admin"))
    assert res.status_code == 200
    assert res.json()["data"]["deleted"] is True


@pytest.mark.asyncio
async def test_delete_config_non_admin_403(client):
    _override(configs=[_config(cid="c1", pid="p1")])
    res = await client.delete("/api/v1/warehouse/config/c1", headers=_headers("ppic"))
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_validation_run_flag(client):
    run = SimpleNamespace(id="r1", user_id=USER_SUB)
    _override(
        run=run,
        results=[_result("p1", values=[40, 40])],
        configs=[_config(pid="p1", capacity=100)],
    )
    res = await client.get("/api/v1/forecast/runs/r1/warehouse-validation", headers=_headers("ppic"))
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["is_within_capacity"] is True
    assert float(data["details"][0]["required_qty"]) == pytest.approx(80)


@pytest.mark.asyncio
async def test_validation_run_tanpa_config_404(client):
    run = SimpleNamespace(id="r1", user_id=USER_SUB)
    _override(run=run, results=[])
    res = await client.get("/api/v1/forecast/runs/r1/warehouse-validation", headers=_headers("ppic"))
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "WAREHOUSE_CONFIG_NOT_FOUND"
