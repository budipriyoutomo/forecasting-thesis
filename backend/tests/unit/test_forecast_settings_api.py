"""
Fase 11.2a — endpoint /forecast-settings. RBAC: baca semua role, tulis admin.
"""
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.api.deps import get_forecast_settings_service
from app.config import get_settings
from app.main import app
from app.services.forecast_settings_service import ForecastSettingsService
from tests.unit.test_forecast_settings_service import FakeSettingsRepo, _factory

settings = get_settings()
BASE = "/api/v1/forecast-settings"


def _headers(role: str) -> dict:
    payload = {
        "sub": "00000000-0000-0000-0000-000000000009",
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


def _override(row=None):
    repo = FakeSettingsRepo(row)
    app.dependency_overrides[get_forecast_settings_service] = lambda: ForecastSettingsService(
        repo, factory=_factory
    )
    return repo


@pytest.fixture(autouse=True)
def _clear():
    yield
    app.dependency_overrides.pop(get_forecast_settings_service, None)


@pytest.mark.asyncio
async def test_get_default(client):
    _override()
    res = await client.get(BASE, headers=_headers("viewer"))

    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["ranking_metric"] == "mad"
    assert body["data"]["updated_at"] is None
    assert body["data"]["enabled_methods"] is None  # belum diatur = semua metode
    assert "moving_average" in body["data"]["available_methods"]
    assert "ets" not in body["data"]["available_methods"]


@pytest.mark.asyncio
async def test_get_tanpa_token_401(client):
    _override()
    res = await client.get(BASE)
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_put_admin(client):
    repo = _override()
    res = await client.put(BASE, json={"ranking_metric": "mape"}, headers=_headers("admin"))

    assert res.status_code == 200
    assert res.json()["data"]["ranking_metric"] == "mape"
    assert res.json()["data"]["updated_at"] is not None
    assert repo.row.ranking_metric == "mape"


@pytest.mark.asyncio
async def test_put_non_admin_403(client):
    _override()
    res = await client.put(BASE, json={"ranking_metric": "mape"}, headers=_headers("viewer"))

    assert res.status_code == 403
    assert res.json()["error"]["code"] == "AUTH_FORBIDDEN"


@pytest.mark.asyncio
async def test_put_tanpa_token_401(client):
    _override()
    res = await client.put(BASE, json={"ranking_metric": "mape"})
    assert res.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("metric", ["mse", "rmse", "", None])
async def test_put_metrik_tidak_valid_422(client, metric):
    repo = _override()
    res = await client.put(BASE, json={"ranking_metric": metric}, headers=_headers("admin"))

    assert res.status_code == 422
    assert repo.saved == 0


@pytest.mark.asyncio
async def test_put_enabled_methods(client):
    repo = _override()
    res = await client.put(
        BASE,
        json={"ranking_metric": "mad", "enabled_methods": ["xgboost", "moving_average"]},
        headers=_headers("admin"),
    )

    assert res.status_code == 200
    assert res.json()["data"]["enabled_methods"] == ["moving_average", "xgboost"]
    assert repo.row.enabled_methods == ["moving_average", "xgboost"]


@pytest.mark.asyncio
async def test_put_enabled_methods_kosong_422(client):
    repo = _override()
    res = await client.put(BASE, json={"ranking_metric": "mad", "enabled_methods": []}, headers=_headers("admin"))

    assert res.status_code == 422
    assert repo.saved == 0


@pytest.mark.asyncio
async def test_put_metode_tak_dikenal_400(client):
    _override()
    res = await client.put(
        BASE, json={"ranking_metric": "mad", "enabled_methods": ["prophet"]}, headers=_headers("admin")
    )

    assert res.status_code == 400
    assert res.json()["error"]["code"] == "UNSUPPORTED_FORECAST_METHOD"


@pytest.mark.asyncio
async def test_get_menyertakan_opsi_engine_default(client):
    _override()
    data = (await client.get(BASE, headers=_headers("viewer"))).json()["data"]

    assert data["es_alpha_grid"] == [0.01, 0.05, 0.15, 0.2, 0.8, 0.95, 0.99]
    assert data["es_alpha_metric"] == "mad"
    assert data["ml_grid_search"] is False
    assert data["ml_winsorize"] is False


@pytest.mark.asyncio
async def test_put_opsi_engine(client):
    repo = _override()
    res = await client.put(
        BASE,
        json={"ranking_metric": "mad", "es_alpha_grid": [0.2, 0.8], "ml_grid_search": True},
        headers=_headers("admin"),
    )
    assert res.status_code == 200
    assert res.json()["data"]["es_alpha_grid"] == [0.2, 0.8]
    assert repo.row.ml_grid_search is True


@pytest.mark.asyncio
@pytest.mark.parametrize("grid", [[], [0], [1], [1.5], [-0.1]])
async def test_put_alpha_di_luar_0_1_422(client, grid):
    repo = _override()
    res = await client.put(BASE, json={"ranking_metric": "mad", "es_alpha_grid": grid}, headers=_headers("admin"))
    assert res.status_code == 422
    assert repo.saved == 0


@pytest.mark.asyncio
async def test_get_dan_put_perencanaan(client):
    repo = _override()
    data = (await client.get(BASE, headers=_headers("viewer"))).json()["data"]
    assert data["service_level_pct"] == 95 and data["eoq_method"] == "classic"

    res = await client.put(
        BASE, json={"ranking_metric": "mad", "service_level_pct": 99, "eoq_method": "dynamic"}, headers=_headers("admin")
    )
    assert res.json()["data"]["service_level_pct"] == 99
    assert repo.row.eoq_method == "dynamic"


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [{"service_level_pct": 50}, {"service_level_pct": 100}, {"eoq_method": "wilson"}])
async def test_put_perencanaan_invalid_422(client, body):
    _override()
    res = await client.put(BASE, json={"ranking_metric": "mad", **body}, headers=_headers("admin"))
    assert res.status_code == 422
