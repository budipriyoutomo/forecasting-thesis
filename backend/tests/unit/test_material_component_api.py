"""Fase 11.3 — endpoint komponen material & tree BOM."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest

from app.api.deps import get_material_component_service
from app.config import get_settings
from app.main import app
from tests.unit.test_material_component_service import _svc

settings = get_settings()


def _headers(role):
    payload = {"sub": "00000000-0000-0000-0000-000000000009", "role": role,
               "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
    return {"Authorization": f"Bearer {jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)}"}


def _override(rows=None):
    svc, repo = _svc(rows)
    app.dependency_overrides[get_material_component_service] = lambda: svc
    return repo


@pytest.fixture(autouse=True)
def _clear():
    yield
    app.dependency_overrides.pop(get_material_component_service, None)


@pytest.mark.asyncio
async def test_create_list_delete(client):
    repo = _override()
    res = await client.post(
        "/api/v1/materials/btl/components", json={"component_material_id": "pre", "qty_per_unit": 1},
        headers=_headers("admin"),
    )
    assert res.status_code == 201
    cid = res.json()["data"]["id"]

    res = await client.get("/api/v1/materials/btl/components", headers=_headers("viewer"))
    assert res.json()["data"][0]["component_material_id"] == "pre"

    res = await client.delete(f"/api/v1/material-components/{cid}", headers=_headers("admin"))
    assert res.status_code == 200 and repo.rows == []


@pytest.mark.asyncio
async def test_siklus_422_dan_viewer_403(client):
    _override([SimpleNamespace(id="c1", parent_material_id="btl", component_material_id="pre", qty_per_unit=1)])
    res = await client.post(
        "/api/v1/materials/pre/components", json={"component_material_id": "btl", "qty_per_unit": 1},
        headers=_headers("admin"),
    )
    assert res.status_code == 422 and res.json()["error"]["code"] == "BOM_CYCLE_DETECTED"
    res = await client.post(
        "/api/v1/materials/btl/components", json={"component_material_id": "cap", "qty_per_unit": 1},
        headers=_headers("viewer"),
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_qty_tidak_positif_422(client):
    _override()
    res = await client.post(
        "/api/v1/materials/btl/components", json={"component_material_id": "pre", "qty_per_unit": 0},
        headers=_headers("admin"),
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_tree_dan_404(client):
    _override([SimpleNamespace(id="c1", parent_material_id="btl", component_material_id="pre", qty_per_unit=1)])
    res = await client.get("/api/v1/boms/tree?product_id=p1", headers=_headers("viewer"))
    assert res.status_code == 200
    assert res.json()["data"]["children"][0]["children"][0]["code"] == "PRE-WHITE"

    res = await client.get("/api/v1/boms/tree?product_id=zz", headers=_headers("viewer"))
    assert res.status_code == 404
    res = await client.delete("/api/v1/material-components/zz", headers=_headers("admin"))
    assert res.json()["error"]["code"] == "MATERIAL_COMPONENT_NOT_FOUND"
