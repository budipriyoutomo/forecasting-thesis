"""
Fase 11.5 — stok awal ERP (snapshot) (REVISI_V2 §3.3).

Snapshot import (CSV/XLSX): material_code, snapshot_date, qty [, uom] — kunci (material,
tanggal) ditimpa. Kedatangan manual dihapus 20 Nov 2026 (kedatangan = hasil ROP).
"""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.inventory_data_service import StockSnapshotService
from app.utils.exceptions import UploadInvalidFormatError


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
        # Regresi 23 Nov 2026 — dulu lolos validasi lalu crash di DB → 500 INTERNAL_ERROR.
        (b"material_code,snapshot_date,qty\nCAP-WHITE,,1\n", "snapshot_date.*wajib"),
        (b"material_code,snapshot_date,qty\nCAP-WHITE,2026-10-01,Infinity\n", "qty"),
        (b"material_code,snapshot_date,qty\nCAP-WHITE,2026-10-01,1e20\n", "terlalu besar"),
        (b"material_code,snapshot_date,qty,uom\nCAP-WHITE,2026-10-01,1,PIECES-PER-CARTON-BOX-XL\n", "uom"),
        # Template menjanjikan YYYY-MM-DD; dd/mm dulu diam-diam terbaca bulan/hari (05/10 → 10 Mei).
        (b"material_code,snapshot_date,qty\nCAP-WHITE,05/10/2026,1\n", "YYYY-MM-DD"),
        (b"material_code,snapshot_date,qty\n,,\n", "tidak berisi baris data"),
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
async def test_import_snapshot_lewati_baris_kosong_nomor_baris_tetap():
    repo = FakeSnapshotRepo()
    svc = StockSnapshotService(repo, Materials([CAP, BTL]), factory=_ns)
    body = b"material_code,snapshot_date,qty\nCAP-WHITE,2026-10-01,1\n,,\nBTL-WHITE,2026-10-01,2\n,,\n"
    assert await svc.import_snapshots("s.csv", body) == {"imported": 2}

    bad = b"material_code,snapshot_date,qty\nCAP-WHITE,2026-10-01,1\n,,\nXX,2026-10-01,2\n"
    with pytest.raises(UploadInvalidFormatError, match="Baris 4"):
        await svc.import_snapshots("s.csv", bad)


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


@pytest.mark.parametrize(
    "body,expected",
    [
        # 23 Nov 2026 — CSV Excel Indonesia: pemisah ';' + desimal koma.
        (b"material_code;snapshot_date;qty\nCAP-WHITE;2026-10-01;350,5\n", 350.5),
        (b"material_code,snapshot_date,qty\nCAP-WHITE,2026-10-01,\"350,5\"\n", 350.5),
        (b"material_code,snapshot_date,qty\nCAP-WHITE,2026-10-01,350.5\n", 350.5),
        (b"material_code;snapshot_date;qty\nCAP-WHITE;2026-10-01;1.234,5\n", 1234.5),
    ],
)
@pytest.mark.asyncio
async def test_import_snapshot_desimal_koma(body, expected):
    repo = FakeSnapshotRepo()
    svc = StockSnapshotService(repo, Materials([CAP, BTL]), factory=_ns)
    await svc.import_snapshots("s.csv", body)
    assert float(repo.rows[0].qty) == expected


@pytest.mark.asyncio
async def test_import_snapshot_qty_kosong_wajib():
    svc = StockSnapshotService(FakeSnapshotRepo(), Materials([CAP, BTL]), factory=_ns)
    with pytest.raises(UploadInvalidFormatError, match="'qty' wajib diisi"):
        await svc.import_snapshots("s.csv", b"material_code,snapshot_date,qty,uom\nCAP-WHITE,2026-10-01,,PCS\n")
