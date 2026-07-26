"""Fase 6 v3.0 — endpoint /warehouse/config & warehouse-validation. RBAC: PUT admin."""
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
    FakeMaterialRepo,
    FakeValidationRepo,
    _config,
    _material,
    _rec,
    FakeReorderRepo,
)

settings = get_settings()
USER_SUB = "00000000-0000-0000-0000-000000000009"


def _headers(role: str) -> dict:
    payload = {"sub": USER_SUB, "role": role, "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


def _override(run=None, recs=None, materials=None, configs=None):
    app.dependency_overrides[get_warehouse_service] = lambda: WarehouseService(
        config_repo=FakeConfigRepo(configs),
        validation_repo=FakeValidationRepo(),
        reorder_repo=FakeReorderRepo(recs or []),
        materials=FakeMaterialRepo(materials or []),
        forecast_repo=FakeForecastRepo(run),
    )


@pytest.fixture(autouse=True)
def _clear():
    yield
    app.dependency_overrides.pop(get_warehouse_service, None)


@pytest.mark.asyncio
async def test_get_config_belum_ada_404(client):
    _override()
    res = await client.get("/api/v1/warehouse/config", headers=_headers("viewer"))
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "WAREHOUSE_CONFIG_NOT_FOUND"


@pytest.mark.asyncio
async def test_put_config_admin_lalu_get(client):
    _override()
    body = {"warehouse_area_m2": 100, "pallet_dimension": {"length": 1, "width": 1, "height": 1}}
    res = await client.put("/api/v1/warehouse/config", headers=_headers("admin"), json=body)
    assert res.status_code == 200
    assert float(res.json()["data"]["warehouse_area_m2"]) == 100


@pytest.mark.asyncio
async def test_put_config_non_admin_403(client):
    _override()
    body = {"warehouse_area_m2": 100, "pallet_dimension": {"length": 1, "width": 1, "height": 1}}
    res = await client.put("/api/v1/warehouse/config", headers=_headers("ppic"), json=body)
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_validation_run_flag(client):
    run = SimpleNamespace(id="r1", user_id=USER_SUB)
    _override(
        run=run,
        recs=[_rec("M1", ss=100, eoq=400)],
        materials=[_material("M1", 250)],
        configs=[_config(area=100)],
    )
    res = await client.get("/api/v1/forecast/runs/r1/warehouse-validation", headers=_headers("ppic"))
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["is_within_capacity"] is True
    assert float(data["total_pallet_required"]) == pytest.approx(2)
