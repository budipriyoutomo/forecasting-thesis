"""
CR v3.7 — GET /api/v1/forecast/runs/{run_id}/method-comparison (format thesis per metode).

Pola sama dengan test_forecast_api: service dirakit dari fake in-memory, engine asli.
"""
import pytest

from app.api.deps import get_forecast_run_service, get_forecast_selection_service
from app.main import app
from tests.unit.test_forecast_api import _auto_run


@pytest.fixture(autouse=True)
def _clear():
    yield
    app.dependency_overrides.pop(get_forecast_run_service, None)
    app.dependency_overrides.pop(get_forecast_selection_service, None)


@pytest.mark.asyncio
async def test_method_comparison_200_envelope(client, auth_headers, smooth_df):
    data = await _auto_run(client, auth_headers, smooth_df, pids=("p1", "p2"))
    run_id = data["run"]["run_id"]

    res = await client.get(f"/api/v1/forecast/runs/{run_id}/method-comparison", headers=auth_headers)

    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    out = body["data"]
    assert out["run_id"] == run_id
    assert out["criteria"] == ["mad", "mape", "mfe"]
    assert len(out["periods"]) == 7
    assert out["methods"][0]["method"] == "random_forest"  # urutan format thesis
    first = out["methods"][0]
    assert [r["product_id"] for r in first["rows"]] == ["p1", "p2"]
    assert set(first["rows"][0]["forecast"]) == set(out["periods"])
    assert first["average"]["n_total"] == 2
    sel = out["run_selection"]
    # satu sumber kebenaran: metode terbaik level run = metode global yang dipakai run
    assert sel["best_method"] == data["results"][0]["selection_analysis"]["best_method"]
    assert sel["ranking"][0]["rank"] == 1
    assert sel["summary"]
    assert [p["product_id"] for p in out["product_methods"]] == ["p1", "p2"]
    assert all(p["is_overridden"] is False for p in out["product_methods"])


@pytest.mark.asyncio
async def test_method_comparison_setelah_override(client, auth_headers, smooth_df):
    data = await _auto_run(client, auth_headers, smooth_df)
    run_id = data["run"]["run_id"]
    best = data["results"][0]["method_used"]
    other = next(c["method"] for c in data["results"][0]["candidates_evaluated"] if c["method"] != best)
    await client.post(
        f"/api/v1/forecast/results/{data['results'][0]['id']}/selection",
        headers=auth_headers,
        json={"method": other, "reason": "Standar planner"},
    )

    out = (await client.get(f"/api/v1/forecast/runs/{run_id}/method-comparison", headers=auth_headers)).json()["data"]

    assert out["run_selection"]["best_method"] == best
    assert out["product_methods"][0] == {
        "product_id": "p1", "status": "COMPLETED", "system_method": best, "method_used": other, "is_overridden": True,
    }


@pytest.mark.asyncio
async def test_method_comparison_run_tidak_ada_404(client, auth_headers, smooth_df):
    await _auto_run(client, auth_headers, smooth_df)

    res = await client.get("/api/v1/forecast/runs/ghost/method-comparison", headers=auth_headers)

    assert res.status_code == 404
    assert res.json()["success"] is False
    assert res.json()["error"]["code"] == "FORECAST_RUN_NOT_FOUND"


@pytest.mark.asyncio
async def test_method_comparison_tanpa_token_401(client, auth_headers, smooth_df):
    data = await _auto_run(client, auth_headers, smooth_df)

    res = await client.get(f"/api/v1/forecast/runs/{data['run']['run_id']}/method-comparison")

    assert res.status_code == 401
