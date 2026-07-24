"""
Fase 5 — endpoint /api/v1/reorder (AGENTS.md §3, §4). Service di-override (fake).
"""
import pytest

from app.api.deps import get_reorder_service
from app.main import app
from app.services.reorder_service import ReorderService
from tests.unit.test_reorder_service import (
    FakeConsumptionRepo,
    FakeForecastRepo,
    FakeMaterialRepo,
    FakeReorderRepo,
    _material,
    _result,
    _rows,
    _run,
)

USER_SUB = "00000000-0000-0000-0000-000000000001"


def _override(run, results, materials, rows_by_material):
    service = ReorderService(
        reorder_repo=FakeReorderRepo(),
        forecast_repo=FakeForecastRepo(run, results),
        materials=FakeMaterialRepo(materials),
        consumptions=FakeConsumptionRepo(rows_by_material),
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
        [_result("m1")],
        [_material("m1", "RM-001", lead=4)],
        {"m1": _rows([10, 12, 11, 9, 10, 11])},
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
    _override(_run(rid="r1", user=USER_SUB), [], [], {})
    res = await client.post("/api/v1/reorder/recommendations", json={"run_id": "r1"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_generate_run_tidak_ada_404(client, auth_headers):
    _override(None, [], [], {})
    res = await client.post(
        "/api/v1/reorder/recommendations", headers=auth_headers, json={"run_id": "ghost"}
    )
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "FORECAST_RUN_NOT_FOUND"


@pytest.mark.asyncio
async def test_list_recommendations_filter_status(client, auth_headers):
    service = _override(
        _run(rid="r1", user=USER_SUB),
        [_result("m1"), _result("m2")],
        [_material("m1", "RM-001"), _material("m2", "RM-002")],
        {"m1": _rows([10, 12, 11, 9, 10, 11]), "m2": _rows([10, 12, 11, 9, 10, 11])},
    )
    await service.generate_for_run(USER_SUB, "r1", current_stock={"m1": 0, "m2": 100000})

    res = await client.get(
        "/api/v1/reorder/recommendations?run_id=r1&status=overstock", headers=auth_headers
    )

    assert res.status_code == 200
    data = res.json()["data"]
    assert all(r["status"] == "overstock" for r in data)
    assert len(data) >= 1
