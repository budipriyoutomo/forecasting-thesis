"""
Test endpoint POST /api/v1/forecast/runs — mode otomatis & manual
(docs/ARCHITECTURE.md §6.8, AGENTS.md §3 checklist test wajib per endpoint).
"""
import pytest


def _history_payload(df):
    return [{"date": str(row.date), "quantity": float(row.quantity)} for row in df.itertuples()]


@pytest.mark.asyncio
async def test_create_forecast_run_auto_mode(client, auth_headers, smooth_df):
    payload = {"history": _history_payload(smooth_df), "horizon": 7, "method": None}
    response = await client.post("/api/v1/forecast/runs", headers=auth_headers, json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["selection_mode"] == "auto"
    assert len(body["data"]["forecast"]) == 7


@pytest.mark.asyncio
async def test_create_forecast_run_manual_mode(client, auth_headers, smooth_df):
    payload = {"history": _history_payload(smooth_df), "horizon": 7, "method": "ets"}
    response = await client.post("/api/v1/forecast/runs", headers=auth_headers, json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["data"]["selection_mode"] == "manual"
    assert body["data"]["method_used"] == "ets"


@pytest.mark.asyncio
async def test_create_forecast_run_unsupported_method(client, auth_headers, smooth_df):
    payload = {"history": _history_payload(smooth_df), "horizon": 7, "method": "prophet"}
    response = await client.post("/api/v1/forecast/runs", headers=auth_headers, json=payload)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UNSUPPORTED_FORECAST_METHOD"


@pytest.mark.asyncio
async def test_create_forecast_run_insufficient_data(client, auth_headers, too_short_df):
    payload = {"history": _history_payload(too_short_df), "horizon": 7, "method": None}
    response = await client.post("/api/v1/forecast/runs", headers=auth_headers, json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INSUFFICIENT_DATA"


@pytest.mark.asyncio
async def test_create_forecast_run_without_auth(client, smooth_df):
    payload = {"history": _history_payload(smooth_df), "horizon": 7}
    response = await client.post("/api/v1/forecast/runs", json=payload)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"
