"""Fase 11.6 — endpoint proyeksi stok + config gudang material."""
from types import SimpleNamespace

import pytest

from app.api.deps import get_stock_projection_service, get_warehouse_service
from app.main import app
from tests.unit.test_stock_projection_service import _svc
from tests.unit.test_warehouse_service import _service_v2


@pytest.fixture(autouse=True)
def _clear():
    yield
    app.dependency_overrides.pop(get_stock_projection_service, None)
    app.dependency_overrides.pop(get_warehouse_service, None)


@pytest.mark.asyncio
async def test_generate_dan_get(client, auth_headers):
    svc, _ = _svc(run=SimpleNamespace(id="r1", user_id="00000000-0000-0000-0000-000000000001"),
                  recs=[SimpleNamespace(material_id="m1", safety_stock=0, buffer_stock=0, reorder_point=0, eoq_qty=0)])
    app.dependency_overrides[get_stock_projection_service] = lambda: svc

    res = await client.post("/api/v1/forecast/runs/r1/stock-projection", headers=auth_headers)
    assert res.status_code == 200, res.text
    assert res.json()["data"][0]["ending_qty"] == 700

    res = await client.get("/api/v1/forecast/runs/r1/stock-projection?scenario=baseline", headers=auth_headers)
    assert res.json()["data"] == []
    res = await client.get("/api/v1/forecast/runs/zz/stock-projection", headers=auth_headers)
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_config_gudang_material_via_api(client):
    from tests.unit.test_forecast_settings_api import _headers

    svc = _service_v2()
    app.dependency_overrides[get_warehouse_service] = lambda: svc
    body = {"item_type": "material", "material_id": "m1", "capacity_mode": "PALLET",
            "pallet_qty": 10, "dus_per_pallet": 40, "pcs_per_dus": 500}
    res = await client.post("/api/v1/warehouse/config", json=body, headers=_headers("admin"))
    assert res.status_code == 201, res.text
    assert res.json()["data"]["item_type"] == "material" and float(res.json()["data"]["capacity_qty"]) == 200_000

    bad = {**body, "product_id": "p1"}
    assert (await client.post("/api/v1/warehouse/config", json=bad, headers=_headers("admin"))).status_code == 422
