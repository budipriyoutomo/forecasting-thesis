"""
Fase 11.17 — endpoint adjust kapasitas gudang per run:
  POST /forecast/runs/{run_id}/capacity-adjustments/suggest  → usulan (simulasi, tidak disimpan)
  GET  /forecast/runs/{run_id}/capacity-adjustments          → adjust berlaku + riwayat
  POST /forecast/runs/{run_id}/capacity-adjustments          → simpan usulan / custom (201)
  POST /forecast/runs/{run_id}/capacity-adjustments/reset    → kembali ke nilai sistem
"""
from datetime import datetime
from types import SimpleNamespace

import pytest

from app.api.deps import get_capacity_adjustment_service
from app.main import app
from app.utils.exceptions import (
    ForbiddenRoleError,
    ForecastRunNotFoundError,
    MaterialNotFoundError,
    OverrideReasonRequiredError,
)

BASE = "/api/v1/forecast/runs/r1/capacity-adjustments"


def _row(source="custom"):
    return SimpleNamespace(
        id="a1", run_id="r1", material_id="m1", user_id="u1", source=source, service_level_pct=97,
        safety_stock=300, buffer_stock=20, previous_value={"safety_stock": "465"}, reason="alasan",
        created_at=datetime(2026, 11, 19, 10, 0),
    )


class FakeService:
    def __init__(self, error=None):
        self.error = error
        self.saved = None

    def _raise(self):
        if self.error:
            raise self.error

    async def suggest(self, user_id, run_id):
        self._raise()
        return {"status": "adjusted", "target_service_level_pct": 99.0, "iterations": 2, "groups": [], "items": []}

    async def list_active(self, user_id, run_id):
        self._raise()
        return [_row()]

    async def history(self, user_id, run_id):
        return [_row(), _row("suggested")]

    async def save(self, user_id, run_id, source, items, reason):
        self._raise()
        self.saved = (source, items, reason)
        return [_row(source)]

    async def reset(self, user_id, run_id, reason):
        self._raise()
        return 1


@pytest.fixture
def fake():
    svc = FakeService()
    app.dependency_overrides[get_capacity_adjustment_service] = lambda: svc
    yield svc
    app.dependency_overrides.pop(get_capacity_adjustment_service, None)


@pytest.mark.asyncio
async def test_usulan(client, auth_headers, fake):
    res = await client.post(f"{BASE}/suggest", headers=auth_headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["success"] is True and body["data"]["status"] == "adjusted"


@pytest.mark.asyncio
async def test_daftar_berlaku_dan_riwayat(client, auth_headers, fake):
    res = await client.get(BASE, headers=auth_headers)
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["active"][0]["material_id"] == "m1" and data["active"][0]["safety_stock"] == 300
    assert [h["source"] for h in data["history"]] == ["custom", "suggested"]
    assert data["active"][0]["created_at"].startswith("2026-11-19")


@pytest.mark.asyncio
async def test_simpan_custom(client, auth_headers, fake):
    payload = {
        "source": "custom", "reason": "Gudang sewa",
        "items": [{"material_id": "m1", "safety_stock": 300, "buffer_stock": 20}],
    }
    res = await client.post(BASE, json=payload, headers=auth_headers)
    assert res.status_code == 201, res.text
    source, items, reason = fake.saved
    assert source == "custom" and reason == "Gudang sewa"
    assert items == [{"material_id": "m1", "safety_stock": 300.0, "buffer_stock": 20.0, "service_level_pct": None}]
    assert res.json()["data"][0]["source"] == "custom"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"source": "custom", "items": []},
        {"source": "auto", "items": [{"material_id": "m1", "safety_stock": 1, "buffer_stock": 1}]},
        {"source": "custom", "items": [{"material_id": "m1", "safety_stock": -1, "buffer_stock": 1}]},
        {"source": "custom", "items": [{"material_id": "m1", "safety_stock": 1}]},
        {"source": "suggested", "items": [{"material_id": "m1", "safety_stock": 1, "buffer_stock": 1, "service_level_pct": 100}]},
    ],
)
async def test_simpan_validasi_422(client, auth_headers, fake, payload):
    res = await client.post(BASE, json=payload, headers=auth_headers)
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_reset(client, auth_headers, fake):
    res = await client.post(f"{BASE}/reset", json={}, headers=auth_headers)
    assert res.status_code == 200, res.text
    assert res.json()["data"] == {"n_reset": 1}
    res = await client.post(f"{BASE}/reset", headers=auth_headers)
    assert res.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error, status, code",
    [
        (ForecastRunNotFoundError("x"), 404, "FORECAST_RUN_NOT_FOUND"),
        (ForbiddenRoleError("x"), 403, "AUTH_FORBIDDEN"),
        (MaterialNotFoundError("x"), 404, "MATERIAL_NOT_FOUND"),
        (OverrideReasonRequiredError("x"), 400, "OVERRIDE_REASON_REQUIRED"),
    ],
)
async def test_error_dipetakan(client, auth_headers, fake, error, status, code):
    fake.error = error
    payload = {"source": "custom", "items": [{"material_id": "m1", "safety_stock": 1, "buffer_stock": 1}]}
    res = await client.post(BASE, json=payload, headers=auth_headers)
    assert res.status_code == status
    assert res.json()["error"]["code"] == code
    assert (await client.post(f"{BASE}/suggest", headers=auth_headers)).status_code == status


@pytest.mark.asyncio
async def test_tanpa_token_401(client, fake):
    assert (await client.post(f"{BASE}/suggest")).status_code == 401
    assert (await client.get(BASE)).status_code == 401
    assert (await client.post(BASE, json={})).status_code == 401
    assert (await client.post(f"{BASE}/reset")).status_code == 401
