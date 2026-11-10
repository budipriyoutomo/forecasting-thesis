"""
Swap v3.0 — endpoint /api/v1/forecast berbasis PRODUK jadi.

ForecastRunService dirakit dari fake in-memory (tanpa DB) lewat dependency_overrides.
Engine forecasting ASLI dipakai dengan fixture dense.
"""
import pytest

from app.api.deps import (
    get_forecast_run_service,
    get_forecast_selection_service,
    get_forecast_settings_service,
)
from app.main import app
from app.services.forecast_run_service import ForecastRunService
from app.services.forecast_selection_service import ForecastSelectionService
from app.services.override_service import OverrideService
from tests.unit.test_forecast_selection_service import FakeOverrideRepo
from app.services.forecast_settings_service import ForecastSettingsService
from tests.unit.test_forecast_settings_service import FakeSettingsRepo, _factory
from tests.unit.test_forecast_run_service import (
    FakeDemandRepo,
    FakeForecastRepo,
    FakeProductRepo,
    _product,
    _rows,
)


def _override(products, rows_by_product):
    repo = FakeForecastRepo()
    service = ForecastRunService(
        forecast_repo=repo,
        products=FakeProductRepo(products),
        demand=FakeDemandRepo(rows_by_product),
    )
    overrides = FakeOverrideRepo()
    selection = ForecastSelectionService(
        repo, overrides, OverrideService(overrides, {"forecast_result": repo.get_result})
    )
    app.dependency_overrides[get_forecast_run_service] = lambda: service
    app.dependency_overrides[get_forecast_selection_service] = lambda: selection
    return service


@pytest.fixture(autouse=True)
def _clear():
    yield
    app.dependency_overrides.pop(get_forecast_run_service, None)
    app.dependency_overrides.pop(get_forecast_selection_service, None)
    app.dependency_overrides.pop(get_forecast_settings_service, None)


def _override_settings(row=None):
    app.dependency_overrides[get_forecast_settings_service] = lambda: ForecastSettingsService(
        FakeSettingsRepo(row), factory=_factory
    )


@pytest.mark.asyncio
async def test_list_methods(client, auth_headers):
    _override_settings()
    res = await client.get("/api/v1/forecast/methods", headers=auth_headers)

    assert res.status_code == 200
    methods = res.json()["data"]["methods"]
    assert "moving_average" in methods and "xgboost" in methods  # metode aktif v3.0
    assert "ets" not in methods  # legacy, nonaktif default (docs §6.9)


@pytest.mark.asyncio
async def test_list_methods_dari_master_data(client, auth_headers):
    _override_settings(_factory(enabled_methods=["xgboost", "moving_average"]))
    res = await client.get("/api/v1/forecast/methods", headers=auth_headers)

    assert res.json()["data"]["methods"] == ["moving_average", "xgboost"]


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
    result = body["data"]["results"][0]
    assert result["selection_mode"] == "auto"
    assert result["product_id"] == "p1"
    assert result["id"]
    # Fase 11.15 — tanpa pemenang: menunggu planner memilih
    assert result["selection_status"] == "PENDING_SELECTION"
    assert result["method_used"] is None
    assert result["forecast"] == []
    assert all(len(c["forecast"]) == 7 for c in result["candidates_evaluated"])
    assert body["data"]["run"]["n_pending_selection"] == 1
    assert "ranking_metric" not in body["data"]["run"]


@pytest.mark.asyncio
async def test_create_run_manual_mode(client, auth_headers, smooth_df):
    _override([_product("p1", "SKU-001")], {"p1": _rows(smooth_df)})
    payload = {"product_ids": ["p1"], "horizon": 7, "method": "moving_average"}

    res = await client.post("/api/v1/forecast/runs", headers=auth_headers, json=payload)

    assert res.status_code == 201
    assert res.json()["data"]["results"][0]["method_used"] == "moving_average"
    assert res.json()["data"]["results"][0]["selection_mode"] == "manual"
    assert res.json()["data"]["results"][0]["selection_status"] == "SELECTED"
    assert len(res.json()["data"]["results"][0]["forecast"]) == 7
    assert res.json()["data"]["run"]["n_pending_selection"] == 0


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


@pytest.mark.asyncio
async def test_endpoint_material_requirements_sudah_tidak_ada(client, auth_headers, smooth_df):
    """Guard regresi: forecast produk-only — rute breakdown BOM dihapus (404)."""
    _override([_product("p1", "SKU-001")], {"p1": _rows(smooth_df)})
    created = await client.post(
        "/api/v1/forecast/runs", headers=auth_headers, json={"product_ids": ["p1"], "horizon": 7}
    )
    run_id = created.json()["data"]["run"]["run_id"]

    res = await client.get(
        f"/api/v1/forecast/runs/{run_id}/material-requirements", headers=auth_headers
    )

    assert res.status_code == 404


# ── Fase 11.15: planner memilih metode per produk ──


async def _auto_run(client, auth_headers, smooth_df, pids=("p1",)):
    _override([_product(p, f"SKU-{p}") for p in pids], {p: _rows(smooth_df) for p in pids})
    res = await client.post(
        "/api/v1/forecast/runs", headers=auth_headers, json={"product_ids": list(pids), "horizon": 7}
    )
    return res.json()["data"]


@pytest.mark.asyncio
async def test_pilih_metode_per_hasil(client, auth_headers, smooth_df):
    data = await _auto_run(client, auth_headers, smooth_df)
    result_id = data["results"][0]["id"]

    res = await client.post(
        f"/api/v1/forecast/results/{result_id}/selection",
        headers=auth_headers,
        json={"method": "xgboost", "reason": "Pola musiman"},
    )

    assert res.status_code == 200
    out = res.json()["data"]
    assert out["method_used"] == "xgboost"
    assert out["selection_status"] == "SELECTED"
    assert out["selection_reason"] == "Pola musiman"
    assert len(out["forecast"]) == 7

    run = await client.get(f"/api/v1/forecast/runs/{data['run']['run_id']}", headers=auth_headers)
    assert run.json()["data"]["results"][0]["method_used"] == "xgboost"
    assert run.json()["data"]["run"]["n_pending_selection"] == 0


@pytest.mark.asyncio
async def test_pilih_metode_tanpa_alasan_400(client, auth_headers, smooth_df):
    data = await _auto_run(client, auth_headers, smooth_df)

    res = await client.post(
        f"/api/v1/forecast/results/{data['results'][0]['id']}/selection",
        headers=auth_headers,
        json={"method": "xgboost", "reason": " "},
    )

    assert res.status_code == 400
    assert res.json()["error"]["code"] == "OVERRIDE_REASON_REQUIRED"


@pytest.mark.asyncio
async def test_pilih_metode_tidak_tersedia_400(client, auth_headers, smooth_df):
    data = await _auto_run(client, auth_headers, smooth_df)

    res = await client.post(
        f"/api/v1/forecast/results/{data['results'][0]['id']}/selection",
        headers=auth_headers,
        json={"method": "prophet", "reason": "coba"},
    )

    assert res.status_code == 400
    assert res.json()["error"]["code"] == "UNSUPPORTED_FORECAST_METHOD"


@pytest.mark.asyncio
async def test_pilih_metode_hasil_tidak_ada_404(client, auth_headers, smooth_df):
    await _auto_run(client, auth_headers, smooth_df)

    res = await client.post(
        "/api/v1/forecast/results/00000000-0000-0000-0000-00000000dead/selection",
        headers=auth_headers,
        json={"method": "xgboost", "reason": "coba"},
    )

    assert res.status_code == 404
    assert res.json()["error"]["code"] == "OVERRIDE_TARGET_NOT_FOUND"


@pytest.mark.asyncio
async def test_pilih_metode_tanpa_token_401(client, smooth_df, auth_headers):
    data = await _auto_run(client, auth_headers, smooth_df)

    res = await client.post(
        f"/api/v1/forecast/results/{data['results'][0]['id']}/selection",
        json={"method": "xgboost", "reason": "coba"},
    )

    assert res.status_code == 401


@pytest.mark.asyncio
async def test_pilih_metode_semua_produk(client, auth_headers, smooth_df):
    data = await _auto_run(client, auth_headers, smooth_df, pids=("p1", "p2"))
    run_id = data["run"]["run_id"]

    res = await client.post(
        f"/api/v1/forecast/runs/{run_id}/selection",
        headers=auth_headers,
        json={"method": "moving_average", "reason": "Standar planner"},
    )

    assert res.status_code == 200
    out = res.json()["data"]
    assert out["n_selected"] == 2
    assert out["skipped_product_ids"] == []
    assert {r["method_used"] for r in out["results"]} == {"moving_average"}


@pytest.mark.asyncio
async def test_pilih_metode_semua_produk_run_tidak_ada_404(client, auth_headers, smooth_df):
    await _auto_run(client, auth_headers, smooth_df)

    res = await client.post(
        "/api/v1/forecast/runs/ghost/selection",
        headers=auth_headers,
        json={"method": "moving_average", "reason": "x"},
    )

    assert res.status_code == 404
    assert res.json()["error"]["code"] == "FORECAST_RUN_NOT_FOUND"


@pytest.mark.asyncio
async def test_pilih_metode_semua_produk_validasi_422(client, auth_headers, smooth_df):
    data = await _auto_run(client, auth_headers, smooth_df)

    res = await client.post(
        f"/api/v1/forecast/runs/{data['run']['run_id']}/selection",
        headers=auth_headers,
        json={"reason": "x"},
    )

    assert res.status_code == 422
