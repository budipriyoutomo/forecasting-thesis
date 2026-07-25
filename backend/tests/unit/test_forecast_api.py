"""
Swap v3.0 — endpoint /api/v1/forecast berbasis PRODUK jadi.

ForecastRunService dirakit dari fake in-memory (tanpa DB) lewat dependency_overrides.
Engine forecasting ASLI dipakai dengan fixture dense.
"""
import pytest

from app.api.deps import get_forecast_run_service
from app.main import app
from app.services.forecast_run_service import ForecastRunService
from tests.unit.test_forecast_run_service import (
    FakeBomRepo,
    FakeDemandRepo,
    FakeForecastRepo,
    FakeProductRepo,
    _product,
    _rows,
)


def _override(products, rows_by_product):
    service = ForecastRunService(
        forecast_repo=FakeForecastRepo(),
        products=FakeProductRepo(products),
        demand=FakeDemandRepo(rows_by_product),
        boms=FakeBomRepo(),
        requirements=None,
    )
    app.dependency_overrides[get_forecast_run_service] = lambda: service
    return service


@pytest.fixture(autouse=True)
def _clear():
    yield
    app.dependency_overrides.pop(get_forecast_run_service, None)


@pytest.mark.asyncio
async def test_list_methods(client, auth_headers):
    res = await client.get("/api/v1/forecast/methods", headers=auth_headers)

    assert res.status_code == 200
    methods = res.json()["data"]["methods"]
    assert "moving_average" in methods and "xgboost" in methods  # metode aktif v3.0
    assert "ets" not in methods  # legacy, nonaktif default (docs §6.9)


@pytest.mark.asyncio
async def test_create_run_auto_mode(client, auth_headers, smooth_df):
    _override([_product("p1", "SKU-001")], {"p1": _rows(smooth_df)})
    payload = {"product_ids": ["p1"], "horizon": 7, "method": None}

    res = await client.post("/api/v1/forecast/runs", headers=auth_headers, json=payload)

    assert res.status_code == 201
    body = res.json()
    assert body["success"] is True
    assert body["data"]["run"]["status"] == "COMPLETED"
    assert body["data"]["run"]["n_completed"] == 1
    assert body["data"]["results"][0]["selection_mode"] == "auto"
    assert body["data"]["results"][0]["product_id"] == "p1"
    assert len(body["data"]["results"][0]["forecast"]) == 7


@pytest.mark.asyncio
async def test_create_run_manual_mode(client, auth_headers, smooth_df):
    _override([_product("p1", "SKU-001")], {"p1": _rows(smooth_df)})
    payload = {"product_ids": ["p1"], "horizon": 7, "method": "moving_average"}

    res = await client.post("/api/v1/forecast/runs", headers=auth_headers, json=payload)

    assert res.status_code == 201
    assert res.json()["data"]["results"][0]["method_used"] == "moving_average"
    assert res.json()["data"]["results"][0]["selection_mode"] == "manual"


@pytest.mark.asyncio
async def test_create_run_unsupported_method_400(client, auth_headers, smooth_df):
    _override([_product("p1", "SKU-001")], {"p1": _rows(smooth_df)})
    payload = {"product_ids": ["p1"], "horizon": 7, "method": "prophet"}

    res = await client.post("/api/v1/forecast/runs", headers=auth_headers, json=payload)

    assert res.status_code == 400
    assert res.json()["error"]["code"] == "UNSUPPORTED_FORECAST_METHOD"


@pytest.mark.asyncio
async def test_create_run_product_not_found_404(client, auth_headers, smooth_df):
    _override([_product("p1", "SKU-001")], {"p1": _rows(smooth_df)})
    payload = {"product_ids": ["p1", "ghost"], "horizon": 7}

    res = await client.post("/api/v1/forecast/runs", headers=auth_headers, json=payload)

    assert res.status_code == 404
    assert res.json()["error"]["code"] == "PRODUCT_NOT_FOUND"


@pytest.mark.asyncio
async def test_create_run_insufficient_data_ditandai(client, auth_headers, too_short_df):
    _override([_product("p1", "SKU-001")], {"p1": _rows(too_short_df)})
    payload = {"product_ids": ["p1"], "horizon": 7}

    res = await client.post("/api/v1/forecast/runs", headers=auth_headers, json=payload)

    assert res.status_code == 201  # run selesai; kegagalan per produk
    assert res.json()["data"]["results"][0]["status"] == "INSUFFICIENT_DATA"
    assert res.json()["data"]["run"]["n_failed"] == 1


@pytest.mark.asyncio
async def test_create_run_validation_product_ids_kosong_422(client, auth_headers):
    _override([], {})
    res = await client.post(
        "/api/v1/forecast/runs", headers=auth_headers, json={"product_ids": [], "horizon": 7}
    )
    assert res.status_code == 422  # Pydantic (min_length=1)


@pytest.mark.asyncio
async def test_create_run_without_auth(client, smooth_df):
    _override([_product("p1", "SKU-001")], {"p1": _rows(smooth_df)})
    payload = {"product_ids": ["p1"], "horizon": 7}

    res = await client.post("/api/v1/forecast/runs", json=payload)

    assert res.status_code == 401
    assert res.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_get_run_polling(client, auth_headers, smooth_df):
    _override([_product("p1", "SKU-001")], {"p1": _rows(smooth_df)})
    created = await client.post(
        "/api/v1/forecast/runs", headers=auth_headers, json={"product_ids": ["p1"], "horizon": 7}
    )
    run_id = created.json()["data"]["run"]["run_id"]

    res = await client.get(f"/api/v1/forecast/runs/{run_id}", headers=auth_headers)

    assert res.status_code == 200
    assert res.json()["data"]["run"]["run_id"] == run_id


@pytest.mark.asyncio
async def test_get_run_not_found_404(client, auth_headers, smooth_df):
    _override([_product("p1", "SKU-001")], {"p1": _rows(smooth_df)})

    res = await client.get("/api/v1/forecast/runs/ghost-run", headers=auth_headers)

    assert res.status_code == 404
    assert res.json()["error"]["code"] == "FORECAST_RUN_NOT_FOUND"


@pytest.mark.asyncio
async def test_list_results_per_product(client, auth_headers, smooth_df):
    _override([_product("p1", "SKU-001")], {"p1": _rows(smooth_df)})
    await client.post(
        "/api/v1/forecast/runs", headers=auth_headers, json={"product_ids": ["p1"], "horizon": 7}
    )

    res = await client.get("/api/v1/forecast/results?product_id=p1", headers=auth_headers)

    assert res.status_code == 200
    assert len(res.json()["data"]) == 1
    assert res.json()["data"][0]["product_id"] == "p1"
