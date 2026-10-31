"""Fase 11.1 — endpoint /material-usage. Baca semua role, import admin/ppic."""
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest

from app.api.deps import get_material_usage_service
from app.config import get_settings
from app.main import app
from app.services.material_usage_service import MaterialUsageService
from tests.unit.test_material_usage_service import M1, M2, P1, ByCode, FakeBoms, FakeUsageRepo

settings = get_settings()
BASE = "/api/v1/material-usage"


def _headers(role):
    payload = {"sub": "00000000-0000-0000-0000-000000000009", "role": role,
               "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
    return {"Authorization": f"Bearer {jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)}"}


def _override(rows=None):
    repo = FakeUsageRepo(rows)
    app.dependency_overrides[get_material_usage_service] = lambda: MaterialUsageService(
        repo, ByCode([M1, M2]), ByCode([P1]), FakeBoms([]), factory=lambda **kw: SimpleNamespace(**kw)
    )
    return repo


@pytest.fixture(autouse=True)
def _clear():
    yield
    app.dependency_overrides.pop(get_material_usage_service, None)


@pytest.mark.asyncio
async def test_import_dan_waste_factors(client):
    _override()
    files = {"file": ("u.csv", b"material_code,period,actual_usage,standard_usage\nBTL-WHITE,2026-01-01,1030,1000\n", "text/csv")}
    res = await client.post(f"{BASE}/import", files=files, headers=_headers("ppic"))
    assert res.status_code == 200 and res.json()["data"] == {"imported": 1}

    res = await client.get(f"{BASE}/waste-factors", headers=_headers("viewer"))
    assert res.json()["data"] == [{"material_id": "m2", "waste_factor": pytest.approx(1.03)}]


@pytest.mark.asyncio
async def test_list(client):
    _override([SimpleNamespace(material_id="m2", product_id=None, period=date(2026, 1, 1),
                               production_output=None, standard_usage=1000, actual_usage=1030)])
    res = await client.get(BASE, headers=_headers("viewer"))
    assert res.json()["data"][0]["actual_usage"] == 1030


@pytest.mark.asyncio
async def test_import_viewer_403_dan_tanpa_token_401(client):
    _override()
    files = {"file": ("u.csv", b"x", "text/csv")}
    assert (await client.post(f"{BASE}/import", files=files, headers=_headers("viewer"))).status_code == 403
    assert (await client.get(BASE)).status_code == 401


@pytest.mark.asyncio
async def test_import_invalid_400(client):
    _override()
    files = {"file": ("u.csv", b"material_code,period\nA,2026-01-01\n", "text/csv")}
    res = await client.post(f"{BASE}/import", files=files, headers=_headers("admin"))
    assert res.status_code == 400 and res.json()["error"]["code"] == "UPLOAD_INVALID_FORMAT"
