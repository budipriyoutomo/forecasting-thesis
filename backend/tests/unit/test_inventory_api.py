"""Fase 11.5 — endpoint stok ERP & kedatangan material."""
from datetime import date, datetime, timedelta, timezone

import jwt
import pytest

from app.api.deps import get_material_receipt_service, get_stock_snapshot_service
from app.config import get_settings
from app.main import app
from app.services.inventory_data_service import MaterialReceiptService, StockSnapshotService
from tests.unit.test_inventory_data_service import (
    BTL,
    CAP,
    FakeReceiptRepo,
    FakeSnapshotRepo,
    Materials,
    _ns,
    _snap,
)

settings = get_settings()


def _headers(role):
    payload = {"sub": "00000000-0000-0000-0000-000000000009", "role": role,
               "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
    return {"Authorization": f"Bearer {jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)}"}


@pytest.fixture(autouse=True)
def _overrides():
    snaps = FakeSnapshotRepo([_snap("m1", date(2026, 9, 1), 100)])
    receipts = FakeReceiptRepo()
    app.dependency_overrides[get_stock_snapshot_service] = lambda: StockSnapshotService(snaps, Materials([CAP, BTL]), factory=_ns)
    app.dependency_overrides[get_material_receipt_service] = lambda: MaterialReceiptService(
        receipts, Materials([CAP, BTL]), factory=_ns
    )
    yield snaps, receipts
    app.dependency_overrides.pop(get_stock_snapshot_service, None)
    app.dependency_overrides.pop(get_material_receipt_service, None)


@pytest.mark.asyncio
async def test_snapshot_import_list_latest(client, _overrides):
    files = {"file": ("s.csv", b"material_code,snapshot_date,qty\nCAP-WHITE,2026-10-01,150\n", "text/csv")}
    res = await client.post("/api/v1/stock-snapshots/import", files=files, headers=_headers("ppic"))
    assert res.json()["data"] == {"imported": 1}

    res = await client.get("/api/v1/stock-snapshots?material_id=m1", headers=_headers("viewer"))
    assert len(res.json()["data"]) == 2
    res = await client.get("/api/v1/stock-snapshots/latest", headers=_headers("viewer"))
    assert res.json()["data"] == [{"material_id": "m1", "snapshot_date": "2026-10-01", "qty": 150.0}]


@pytest.mark.asyncio
async def test_snapshot_import_viewer_403_invalid_400(client):
    files = {"file": ("s.csv", b"material_code,snapshot_date,qty\nXX,2026-10-01,1\n", "text/csv")}
    assert (await client.post("/api/v1/stock-snapshots/import", files=files, headers=_headers("viewer"))).status_code == 403
    res = await client.post("/api/v1/stock-snapshots/import", files=files, headers=_headers("admin"))
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_receipt_crud_dan_import(client, _overrides):
    _, receipts = _overrides
    body = {"material_id": "m1", "expected_date": "2026-11-05", "qty": 500, "note": "PO-1"}
    res = await client.post("/api/v1/material-receipts", json=body, headers=_headers("ppic"))
    assert res.status_code == 201
    rid = res.json()["data"]["id"]
    assert res.json()["data"]["source"] == "manual"

    res = await client.put(f"/api/v1/material-receipts/{rid}", json={"qty": 600}, headers=_headers("ppic"))
    assert res.json()["data"]["qty"] == 600

    files = {"file": ("k.csv", b"material_code,expected_date,qty\nBTL-WHITE,2026-11-20,300\n", "text/csv")}
    res = await client.post("/api/v1/material-receipts/import", files=files, headers=_headers("admin"))
    assert res.json()["data"] == {"imported": 1}

    res = await client.get("/api/v1/material-receipts?date_from=2026-11-10", headers=_headers("viewer"))
    assert [r["material_id"] for r in res.json()["data"]] == ["m2"]

    res = await client.delete(f"/api/v1/material-receipts/{rid}", headers=_headers("admin"))
    assert res.status_code == 200 and len(receipts.rows) == 1


@pytest.mark.asyncio
async def test_receipt_404_422_401(client):
    res = await client.delete("/api/v1/material-receipts/nope", headers=_headers("admin"))
    assert res.status_code == 404 and res.json()["error"]["code"] == "MATERIAL_RECEIPT_NOT_FOUND"
    res = await client.post(
        "/api/v1/material-receipts", json={"material_id": "m1", "expected_date": "2026-11-05", "qty": 0},
        headers=_headers("admin"),
    )
    assert res.status_code == 422
    assert (await client.get("/api/v1/material-receipts")).status_code == 401
