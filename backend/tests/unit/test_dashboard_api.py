"""
Fase 7 — endpoint /api/v1/dashboard/summary (AGENTS.md §3, §4).
"""
import pytest

from app.api.deps import get_dashboard_service
from app.main import app
from app.services.dashboard_service import DashboardService
from tests.unit.test_dashboard_service import (
    FakeForecast,
    FakeMaterials,
    FakeOverride,
    FakeReorder,
    _rec,
    _result,
)
from types import SimpleNamespace


def _override():
    run = SimpleNamespace(id="r1", status="COMPLETED")
    service = DashboardService(
        FakeMaterials(2),
        FakeForecast(run, [_result(mase=0.4)]),
        FakeReorder([_rec("urgent")]),
        FakeOverride([object()]),
    )
    app.dependency_overrides[get_dashboard_service] = lambda: service


@pytest.fixture(autouse=True)
def _clear():
    yield
    app.dependency_overrides.pop(get_dashboard_service, None)


@pytest.mark.asyncio
async def test_summary_200(client, auth_headers):
    _override()

    res = await client.get("/api/v1/dashboard/summary", headers=auth_headers)

    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["n_materials"] == 2
    assert body["data"]["latest_run"]["n_completed"] == 1
    assert body["data"]["reorder_status_counts"]["urgent"] == 1


@pytest.mark.asyncio
async def test_summary_tanpa_auth_401(client):
    _override()
    res = await client.get("/api/v1/dashboard/summary")
    assert res.status_code == 401
