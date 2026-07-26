"""
Fase 6 — endpoint /api/v1/overrides (AGENTS.md §3, §4, §5).
"""
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.api.deps import get_override_service
from app.main import app
from app.services.override_service import OverrideService
from tests.unit.test_override_service import FakeOverrideRepo


def _target():
    return SimpleNamespace(
        id="rec1",
        safety_stock=Decimal("6.6"),
        reorder_point=Decimal("46.6"),
        recommended_order_qty=Decimal("87"),
        status="urgent",
    )


def _override_service(store):
    async def resolver(tid):
        return store.get(str(tid))

    service = OverrideService(FakeOverrideRepo(), {"reorder_recommendation": resolver})
    app.dependency_overrides[get_override_service] = lambda: service
    return service


@pytest.fixture(autouse=True)
def _clear():
    yield
    app.dependency_overrides.pop(get_override_service, None)


@pytest.mark.asyncio
async def test_create_override_201(client, auth_headers):
    _override_service({"rec1": _target()})

    res = await client.post(
        "/api/v1/overrides",
        headers=auth_headers,
        json={
            "target_type": "reorder_recommendation",
            "target_id": "rec1",
            "new_value": {"recommended_order_qty": 120},
            "reason": "Rencana produksi tambahan",
        },
    )

    assert res.status_code == 201
    data = res.json()["data"]
    assert data["new_value"] == {"recommended_order_qty": 120}
    assert data["previous_value"]["recommended_order_qty"] == "87"


@pytest.mark.asyncio
async def test_create_override_material_requirement_201(client, auth_headers):
    # Fase 8: target_type `material_requirement` diterima (Literal schema diperluas).
    target = SimpleNamespace(
        id="mr1",
        forecast_qty=Decimal("1200"),
        standard_usage_qty=Decimal("1150"),
        actual_usage_qty=Decimal("1180"),
        buffer_stock_pct=Decimal("5"),
    )

    async def resolver(tid):
        return {"mr1": target}.get(str(tid))

    service = OverrideService(FakeOverrideRepo(), {"material_requirement": resolver})
    app.dependency_overrides[get_override_service] = lambda: service

    res = await client.post(
        "/api/v1/overrides",
        headers=auth_headers,
        json={
            "target_type": "material_requirement",
            "target_id": "mr1",
            "new_value": {"forecast_qty": 1300},
            "reason": "Koreksi kebutuhan material",
        },
    )

    assert res.status_code == 201
    assert res.json()["data"]["previous_value"]["forecast_qty"] == "1200"


@pytest.mark.asyncio
async def test_create_override_reason_kosong_400(client, auth_headers):
    _override_service({"rec1": _target()})

    res = await client.post(
        "/api/v1/overrides",
        headers=auth_headers,
        json={"target_type": "reorder_recommendation", "target_id": "rec1", "new_value": {"q": 1}, "reason": "  "},
    )

    assert res.status_code == 400
    assert res.json()["error"]["code"] == "OVERRIDE_REASON_REQUIRED"


@pytest.mark.asyncio
async def test_create_override_target_type_invalid_422(client, auth_headers):
    _override_service({"rec1": _target()})

    res = await client.post(
        "/api/v1/overrides",
        headers=auth_headers,
        json={"target_type": "material", "target_id": "rec1", "new_value": {"q": 1}, "reason": "x"},
    )

    assert res.status_code == 422  # Literal Pydantic


@pytest.mark.asyncio
async def test_create_override_target_tidak_ada_404(client, auth_headers):
    _override_service({})

    res = await client.post(
        "/api/v1/overrides",
        headers=auth_headers,
        json={"target_type": "reorder_recommendation", "target_id": "ghost", "new_value": {"q": 1}, "reason": "x"},
    )

    assert res.status_code == 404
    assert res.json()["error"]["code"] == "OVERRIDE_TARGET_NOT_FOUND"


@pytest.mark.asyncio
async def test_create_override_tanpa_auth_401(client):
    _override_service({"rec1": _target()})

    res = await client.post(
        "/api/v1/overrides",
        json={"target_type": "reorder_recommendation", "target_id": "rec1", "new_value": {"q": 1}, "reason": "x"},
    )

    assert res.status_code == 401


@pytest.mark.asyncio
async def test_list_audit_trail(client, auth_headers):
    service = _override_service({"rec1": _target()})
    await service.create("u", "reorder_recommendation", "rec1", {"q": 100}, "a1")
    await service.create("u", "reorder_recommendation", "rec1", {"q": 120}, "a2")

    res = await client.get("/api/v1/overrides?target_id=rec1", headers=auth_headers)

    assert res.status_code == 200
    assert len(res.json()["data"]) == 2
