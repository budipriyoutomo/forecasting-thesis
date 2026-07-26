"""
Swap v3.0 — endpoint /api/v1/reorder. Service di-override (fake), reorder per
material dari breakdown BOM atas forecast produk.
"""
import pytest

from app.api.deps import get_reorder_service
from app.main import app
from app.services.reorder_service import ReorderService
from tests.unit.test_reorder_service import (
    FakeBomRepo,
    FakeForecastRepo,
    FakeMaterialRepo,
    FakeReorderRepo,
    _bom,
    _material,
    _result,
    _run,
)

USER_SUB = "00000000-0000-0000-0000-000000000001"


def _override(run, results, boms_by_product, materials):
    service = ReorderService(
        reorder_repo=FakeReorderRepo(),
        forecast_repo=FakeForecastRepo(run, results),
        boms=FakeBomRepo(boms_by_product),
        materials=FakeMaterialRepo(materials),
    )
    app.dependency_overrides[get_reorder_service] = lambda: service
    return service


@pytest.fixture(autouse=True)
def _clear():
    yield
    app.dependency_overrides.pop(get_reorder_service, None)


@pytest.mark.asyncio
async def test_generate_recommendations_201(client, auth_headers):
    _override(
        _run(rid="r1", user=USER_SUB),
        [_result("p1", [10, 12, 11, 9, 10, 11])],
        {"p1": [_bom("p1", "m1", 1)]},
        [_material("m1", "RM-001", lead=4)],
    )

    res = await client.post(
        "/api/v1/reorder/recommendations",
        headers=auth_headers,
        json={"run_id": "r1", "current_stock": {"m1": 0}},
    )

    assert res.status_code == 201
    data = res.json()["data"]
    assert len(data) == 1
    assert data[0]["status"] in ("urgent", "safe", "overstock")
    assert float(data[0]["reorder_point"]) > 0


@pytest.mark.asyncio
async def test_generate_tanpa_auth_401(client):
    _override(_run(rid="r1", user=USER_SUB), [], {}, [])
    res = await client.post("/api/v1/reorder/recommendations", json={"run_id": "r1"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_generate_run_tidak_ada_404(client, auth_headers):
    _override(None, [], {}, [])
    res = await client.post(
        "/api/v1/reorder/recommendations", headers=auth_headers, json={"run_id": "ghost"}
    )
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "FORECAST_RUN_NOT_FOUND"


@pytest.mark.asyncio
async def test_list_recommendations_filter_status(client, auth_headers):
    service = _override(
        _run(rid="r1", user=USER_SUB),
        [_result("p1", [10, 12, 11, 9, 10, 11])],
        {"p1": [_bom("p1", "m1", 1), _bom("p1", "m2", 1)]},
        [_material("m1", "RM-001"), _material("m2", "RM-002")],
    )
    await service.generate_for_run(USER_SUB, "r1", current_stock={"m1": 0, "m2": 100000})

    res = await client.get(
        "/api/v1/reorder/recommendations?run_id=r1&status=overstock", headers=auth_headers
    )

    assert res.status_code == 200
    data = res.json()["data"]
    assert all(r["status"] == "overstock" for r in data)
    assert len(data) >= 1
