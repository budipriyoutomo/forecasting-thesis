"""Fase 11.5 — endpoint stok ERP. Kedatangan manual dihapus 20 Nov 2026 (kedatangan = hasil ROP)."""
from datetime import date, datetime, timedelta, timezone

import jwt
import pytest

from app.api.deps import get_stock_snapshot_service
from app.config import get_settings
from app.main import app
from app.services.inventory_data_service import StockSnapshotService
from tests.unit.test_inventory_data_service import (
    BTL,
    CAP,
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
    app.dependency_overrides[get_stock_snapshot_service] = lambda: StockSnapshotService(snaps, Materials([CAP, BTL]), factory=_ns)
    yield snaps
    app.dependency_overrides.pop(get_stock_snapshot_service, None)


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
@pytest.mark.parametrize(
    "method, path",
    [
        ("get", "/api/v1/material-receipts"),
        ("post", "/api/v1/material-receipts"),
        ("post", "/api/v1/material-receipts/import"),
        ("put", "/api/v1/material-receipts/r1"),
        ("delete", "/api/v1/material-receipts/r1"),
    ],
)
async def test_endpoint_kedatangan_manual_dihapus(client, method, path):
    # 20 Nov 2026: kedatangan = pesanan hasil ROP (proyeksi stok), bukan input manual/upload
    res = await getattr(client, method)(path, headers=_headers("admin"))
    assert res.status_code == 404
