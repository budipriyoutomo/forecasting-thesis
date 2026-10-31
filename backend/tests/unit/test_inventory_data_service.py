"""
Fase 11.5 — stok awal ERP (snapshot) & estimasi kedatangan material (REVISI_V2 §3.3).

Snapshot import (CSV/XLSX): material_code, snapshot_date, qty [, uom] — kunci (material,
tanggal) ditimpa. Kedatangan: input manual (CRUD) atau import material_code,
expected_date, qty [, note].
"""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.schemas.inventory import MaterialReceiptCreate, MaterialReceiptUpdate
from app.services.inventory_data_service import MaterialReceiptService, StockSnapshotService
from app.utils.exceptions import MaterialNotFoundError, MaterialReceiptNotFoundError, UploadInvalidFormatError


class FakeSnapshotRepo:
    def __init__(self, rows=None):
        self.rows = list(rows or [])

    async def upsert(self, rows):
        keys = {(str(r.material_id), r.snapshot_date) for r in rows}
        self.rows = [r for r in self.rows if (str(r.material_id), r.snapshot_date) not in keys] + list(rows)
        return len(rows)

    async def list(self, material_id=None, snapshot_date=None):
        return [
            r for r in self.rows
            if (material_id is None or str(r.material_id) == str(material_id))
            and (snapshot_date is None or r.snapshot_date == snapshot_date)
        ]


class FakeReceiptRepo:
    def __init__(self, rows=None):
        self.rows = list(rows or [])

    async def list(self, material_id=None, date_from=None, date_to=None):
        return [
            r for r in self.rows
            if (material_id is None or str(r.material_id) == str(material_id))
            and (date_from is None or r.expected_date >= date_from)
            and (date_to is None or r.expected_date <= date_to)
        ]

    async def get_by_id(self, rid):
        return next((r for r in self.rows if str(r.id) == str(rid)), None)

    async def add(self, row):
        row.id = row.id or f"r{len(self.rows) + 1}"
        self.rows.append(row)
        return row

    async def add_all(self, rows):
        for r in rows:
            await self.add(r)
        return len(rows)

    async def save(self, row):
        return row

    async def delete(self, row):
        self.rows.remove(row)


class Materials:
    def __init__(self, items):
        self._by_id = {str(m.id): m for m in items}
        self._by_code = {m.code: m for m in items}

    async def get_by_code(self, code):
        return self._by_code.get(code)

    async def get_by_id(self, mid):
        return self._by_id.get(str(mid))

    async def list(self):
        return list(self._by_id.values())


CAP = SimpleNamespace(id="m1", code="CAP-WHITE", unit_price=Decimal("100"))
BTL = SimpleNamespace(id="m2", code="BTL-WHITE", unit_price=None)


def _ns(**kw):
    return SimpleNamespace(id=None, **kw)


def _snap(mid, d, qty):
    return SimpleNamespace(material_id=mid, snapshot_date=d, qty=Decimal(str(qty)), uom=None)


# ── Snapshot ──


@pytest.mark.asyncio
async def test_import_snapshot_dan_timpa_tanggal_sama():
    repo = FakeSnapshotRepo([_snap("m1", date(2026, 10, 1), 5)])
    svc = StockSnapshotService(repo, Materials([CAP, BTL]), factory=_ns)
    body = b"material_code,snapshot_date,qty,uom\nCAP-WHITE,2026-10-01,1200,PCS\nBTL-WHITE,2026-10-01,800,\n"

    assert await svc.import_snapshots("s.csv", body) == {"imported": 2}
    cap = [r for r in repo.rows if r.material_id == "m1"]
    assert len(cap) == 1 and float(cap[0].qty) == 1200 and cap[0].uom == "PCS"


@pytest.mark.parametrize(
    "body,match",
    [
        (b"material_code,snapshot_date\nCAP-WHITE,2026-10-01\n", "qty"),
        (b"material_code,snapshot_date,qty\nXX,2026-10-01,1\n", "Material"),
        (b"material_code,snapshot_date,qty\nCAP-WHITE,2026-10-01,-1\n", "negatif"),
        (b"material_code,snapshot_date,qty\nCAP-WHITE,besok,1\n", "snapshot_date"),
        (b"material_code,snapshot_date,qty\nCAP-WHITE,2026-10-01,1\nCAP-WHITE,2026-10-01,2\n", "duplikat"),
    ],
)
@pytest.mark.asyncio
async def test_import_snapshot_invalid(body, match):
    repo = FakeSnapshotRepo()
    svc = StockSnapshotService(repo, Materials([CAP, BTL]), factory=_ns)
    with pytest.raises(UploadInvalidFormatError, match=match):
        await svc.import_snapshots("s.csv", body)
    assert repo.rows == []


@pytest.mark.asyncio
async def test_latest_stock_per_material_per_tanggal_acuan():
    repo = FakeSnapshotRepo([
        _snap("m1", date(2026, 9, 1), 100), _snap("m1", date(2026, 10, 1), 150),
        _snap("m2", date(2026, 9, 15), 70),
    ])
    svc = StockSnapshotService(repo, Materials([CAP, BTL]), factory=_ns)

    latest = await svc.latest_stock()
    assert latest == {"m1": (date(2026, 10, 1), 150.0), "m2": (date(2026, 9, 15), 70.0)}
    assert (await svc.latest_stock(as_of=date(2026, 9, 20)))["m1"] == (date(2026, 9, 1), 100.0)


@pytest.mark.asyncio
async def test_rata_rata_nilai_persediaan():
    repo = FakeSnapshotRepo([
        _snap("m1", date(2026, 9, 1), 100), _snap("m1", date(2026, 10, 1), 300),
        _snap("m2", date(2026, 10, 1), 999),  # tanpa harga → dilewati
    ])
    svc = StockSnapshotService(repo, Materials([CAP, BTL]), factory=_ns)
    # nilai per tanggal: 9/1 = 100×100 = 10.000 ; 10/1 = 300×100 = 30.000 → rata-rata 20.000
    assert await svc.average_inventory_value() == pytest.approx(20_000)
    assert await StockSnapshotService(FakeSnapshotRepo(), Materials([]), factory=_ns).average_inventory_value() is None


# ── Kedatangan ──


def _receipts(rows=None):
    repo = FakeReceiptRepo(rows)
    return MaterialReceiptService(repo, Materials([CAP, BTL]), factory=_ns), repo


@pytest.mark.asyncio
async def test_crud_kedatangan_manual():
    svc, repo = _receipts()
    r = await svc.create(MaterialReceiptCreate(material_id="m1", expected_date=date(2026, 11, 5), qty=500), user_id="u1")
    assert r.source == "manual" and r.created_by == "u1"

    r = await svc.update(r.id, MaterialReceiptUpdate(qty=600, note="revisi supplier"))
    assert float(r.qty) == 600 and r.note == "revisi supplier"

    await svc.delete(r.id)
    assert repo.rows == []
    with pytest.raises(MaterialReceiptNotFoundError):
        await svc.delete("nope")


@pytest.mark.asyncio
async def test_create_material_tidak_ada_404():
    svc, _ = _receipts()
    with pytest.raises(MaterialNotFoundError):
        await svc.create(MaterialReceiptCreate(material_id="zz", expected_date=date(2026, 11, 5), qty=1), user_id="u1")


def test_qty_kedatangan_harus_positif():
    with pytest.raises(ValueError):
        MaterialReceiptCreate(material_id="m1", expected_date=date(2026, 11, 5), qty=0)


@pytest.mark.asyncio
async def test_import_kedatangan():
    svc, repo = _receipts()
    body = b"material_code,expected_date,qty,note\nCAP-WHITE,2026-11-05,500,PO-1\nBTL-WHITE,2026-11-20,300,\n"
    assert await svc.import_receipts("k.csv", body, user_id="u1") == {"imported": 2}
    assert {r.source for r in repo.rows} == {"upload"}
    assert repo.rows[0].note == "PO-1" and repo.rows[1].note is None


@pytest.mark.asyncio
async def test_import_kedatangan_invalid():
    svc, repo = _receipts()
    with pytest.raises(UploadInvalidFormatError, match="lebih dari 0"):
        await svc.import_receipts("k.csv", b"material_code,expected_date,qty\nCAP-WHITE,2026-11-05,0\n", user_id="u1")
    assert repo.rows == []


@pytest.mark.asyncio
async def test_list_rentang_tanggal():
    svc, _ = _receipts([
        SimpleNamespace(id="r1", material_id="m1", expected_date=date(2026, 11, 5), qty=1),
        SimpleNamespace(id="r2", material_id="m1", expected_date=date(2026, 12, 5), qty=1),
    ])
    rows = await svc.list(date_from=date(2026, 11, 1), date_to=date(2026, 11, 30))
    assert [r.id for r in rows] == ["r1"]
