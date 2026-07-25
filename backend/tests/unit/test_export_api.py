"""
Fase 8 — endpoint export forecast/reorder (AGENTS.md §3). Service di-override.
"""
from types import SimpleNamespace

import pytest

from app.api.deps import get_export_service
from app.main import app
from app.services.export_service import ExportService
from tests.unit.test_export_service import _async, _fresult, _rec

USER_SUB = "00000000-0000-0000-0000-000000000001"


def _make_service(user=USER_SUB, run_exists=True):
    forecast_repo = SimpleNamespace(
        get_run=_async(SimpleNamespace(id="r1", user_id=user) if run_exists else None),
        list_results=_async([_fresult("m1")]),
    )
    reorder_repo = SimpleNamespace(list_by_run=_async([_rec("m1")]))
    return ExportService(forecast_repo, reorder_repo, storage=None)


def _override(service):
    app.dependency_overrides[get_export_service] = lambda: service


@pytest.fixture(autouse=True)
def _clear():
    yield
    app.dependency_overrides.pop(get_export_service, None)


@pytest.mark.asyncio
async def test_export_forecast_xlsx(client, auth_headers):
    _override(_make_service())

    res = await client.get("/api/v1/forecast/runs/r1/export", headers=auth_headers)

    assert res.status_code == 200
    assert "spreadsheetml" in res.headers["content-type"]
    assert res.content[:2] == b"PK"
    assert "attachment" in res.headers["content-disposition"]


@pytest.mark.asyncio
async def test_export_reorder_xlsx(client, auth_headers):
    _override(_make_service())

    res = await client.get("/api/v1/reorder/recommendations/export?run_id=r1", headers=auth_headers)

    assert res.status_code == 200
    assert res.content[:2] == b"PK"


@pytest.mark.asyncio
async def test_export_reorder_pdf(client, auth_headers):
    _override(_make_service())

    res = await client.get(
        "/api/v1/reorder/recommendations/export?run_id=r1&format=pdf", headers=auth_headers
    )

    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content[:4] == b"%PDF"


@pytest.mark.asyncio
async def test_export_format_invalid_422(client, auth_headers):
    _override(_make_service())

    res = await client.get(
        "/api/v1/reorder/recommendations/export?run_id=r1&format=csv", headers=auth_headers
    )

    assert res.status_code == 422  # Literal xlsx|pdf


@pytest.mark.asyncio
async def test_export_tanpa_auth_401(client):
    _override(_make_service())

    res = await client.get("/api/v1/forecast/runs/r1/export")

    assert res.status_code == 401


@pytest.mark.asyncio
async def test_export_run_tidak_ada_404(client, auth_headers):
    _override(_make_service(run_exists=False))

    res = await client.get("/api/v1/forecast/runs/ghost/export", headers=auth_headers)

    assert res.status_code == 404
    assert res.json()["error"]["code"] == "FORECAST_RUN_NOT_FOUND"
