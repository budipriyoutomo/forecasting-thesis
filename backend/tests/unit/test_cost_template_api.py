"""
Fase 10 (2 Oktober 2026) — endpoint /cost-templates. RBAC: tulis admin, baca semua role.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import jwt
import pytest

from app.api.deps import get_cost_template_service
from app.config import get_settings
from app.main import app
from app.services.cost_template_service import CostTemplateService
from tests.unit.test_cost_template_service import (
    ITEMS,
    FakeTemplateRepo,
    FakeWarehouseConfigRepo,
    _item_factory,
    _template_factory,
    _tpl,
)

settings = get_settings()
BASE = "/api/v1/cost-templates"
BODY = {
    "name": "Template 2026",
    "description": "Biaya gudang utama",
    "ordering_cost": 250000,
    "holding_cost": 800,
    "items": [
        {"item_type": "OVERHEAD", "name": "Listrik", "monthly_amount": 3000000},
        {
            "item_type": "STORAGE_ASSET",
            "name": "Rak",
            "purchase_price": 50000000,
            "salvage_value": 5000000,
            "useful_life_months": 60,
            "qty": 10,
        },
    ],
}


def _headers(role: str) -> dict:
    payload = {
        "sub": "00000000-0000-0000-0000-000000000009",
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


def _override(templates=None, configs=None):
    repo = FakeTemplateRepo(templates)
    app.dependency_overrides[get_cost_template_service] = lambda: CostTemplateService(
        repo=repo,
        warehouse_configs=FakeWarehouseConfigRepo(configs),
        template_factory=_template_factory,
        item_factory=_item_factory,
    )


@pytest.fixture(autouse=True)
def _clear():
    yield
    app.dependency_overrides.pop(get_cost_template_service, None)


@pytest.mark.asyncio
async def test_list_kosong(client):
    _override()
    res = await client.get(BASE, headers=_headers("viewer"))
    assert res.status_code == 200
    assert res.json()["data"] == []


@pytest.mark.asyncio
async def test_list_tanpa_token_401(client):
    _override()
    res = await client.get(BASE)
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_create_admin_201_dengan_item_dan_biaya_bulanan(client):
    _override()
    res = await client.post(BASE, headers=_headers("admin"), json=BODY)
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["name"] == "Template 2026"
    assert data["is_active"] is False
    assert float(data["ordering_cost"]) == 250000
    assert float(data["holding_cost"]) == 800
    items = {i["name"]: i for i in data["items"]}
    assert float(items["Listrik"]["monthly_cost"]) == 3000000
    assert float(items["Rak"]["monthly_cost"]) == 7500000  # (50jt − 5jt) ÷ 60 × 10


@pytest.mark.asyncio
async def test_create_non_admin_403(client):
    _override()
    res = await client.post(BASE, headers=_headers("ppic"), json=BODY)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "AUTH_FORBIDDEN"


@pytest.mark.asyncio
async def test_create_nama_duplikat_409(client):
    _override([_tpl(name="Template 2026")])
    res = await client.post(BASE, headers=_headers("admin"), json=BODY)
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "COST_TEMPLATE_NAME_EXISTS"


@pytest.mark.asyncio
async def test_create_item_aset_tanpa_umur_422(client):
    _override()
    body = {**BODY, "items": [{"item_type": "STORAGE_ASSET", "name": "Rak", "purchase_price": 1000}]}
    res = await client.post(BASE, headers=_headers("admin"), json=body)
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_get_by_id(client):
    _override([_tpl()])
    res = await client.get(f"{BASE}/t1", headers=_headers("viewer"))
    assert res.status_code == 200
    assert res.json()["data"]["id"] == "t1"


@pytest.mark.asyncio
async def test_get_tidak_ada_404(client):
    _override()
    res = await client.get(f"{BASE}/ghost", headers=_headers("viewer"))
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "COST_TEMPLATE_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_active(client):
    _override([_tpl("t1", "A"), _tpl("t2", "B", active=True)])
    res = await client.get(f"{BASE}/active", headers=_headers("viewer"))
    assert res.status_code == 200
    assert res.json()["data"]["id"] == "t2"


@pytest.mark.asyncio
async def test_get_active_belum_ada_404(client):
    _override([_tpl()])
    res = await client.get(f"{BASE}/active", headers=_headers("viewer"))
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "COST_TEMPLATE_NOT_FOUND"


@pytest.mark.asyncio
async def test_update_admin(client):
    _override([_tpl()])
    body = {**BODY, "name": "Template 2026 rev", "holding_cost": 900, "items": []}
    res = await client.put(f"{BASE}/t1", headers=_headers("admin"), json=body)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["name"] == "Template 2026 rev"
    assert float(data["holding_cost"]) == 900
    assert data["items"] == []


@pytest.mark.asyncio
async def test_update_non_admin_403(client):
    _override([_tpl()])
    res = await client.put(f"{BASE}/t1", headers=_headers("ppic"), json=BODY)
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_update_tidak_ada_404(client):
    _override()
    res = await client.put(f"{BASE}/ghost", headers=_headers("admin"), json=BODY)
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_activate_admin(client):
    _override([_tpl("t1", "A", active=True), _tpl("t2", "B")])
    res = await client.post(f"{BASE}/t2/activate", headers=_headers("admin"))
    assert res.status_code == 200
    assert res.json()["data"]["is_active"] is True
    listed = (await client.get(BASE, headers=_headers("viewer"))).json()["data"]
    assert [t["id"] for t in listed if t["is_active"]] == ["t2"]


@pytest.mark.asyncio
async def test_activate_non_admin_403(client):
    _override([_tpl()])
    res = await client.post(f"{BASE}/t1/activate", headers=_headers("ppic"))
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_activate_tidak_ada_404(client):
    _override()
    res = await client.post(f"{BASE}/ghost/activate", headers=_headers("admin"))
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_delete_admin(client):
    _override([_tpl()])
    res = await client.delete(f"{BASE}/t1", headers=_headers("admin"))
    assert res.status_code == 200
    assert res.json()["data"]["deleted"] is True


@pytest.mark.asyncio
async def test_delete_non_admin_403(client):
    _override([_tpl()])
    res = await client.delete(f"{BASE}/t1", headers=_headers("ppic"))
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_summary_saran_h(client):
    configs = [SimpleNamespace(capacity_mode="DUS", pallet_qty=0, dus_qty=20000, dus_per_pallet=None)]
    _override([_tpl(items=ITEMS)], configs=configs)
    res = await client.get(f"{BASE}/t1/summary", headers=_headers("viewer"))
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["template_id"] == "t1"
    assert float(data["total_depreciation_monthly"]) == pytest.approx(11510416.6667)
    assert float(data["total_overhead_monthly"]) == 4000000
    assert float(data["total_capacity_dus"]) == 20000
    assert float(data["suggested_holding_cost"]) == pytest.approx(775.5208)
    assert float(data["holding_cost"]) == 800  # H manual yang dipakai EOQ


@pytest.mark.asyncio
async def test_summary_tidak_ada_404(client):
    _override()
    res = await client.get(f"{BASE}/ghost/summary", headers=_headers("viewer"))
    assert res.status_code == 404
