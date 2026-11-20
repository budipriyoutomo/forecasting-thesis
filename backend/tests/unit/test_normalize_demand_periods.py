"""CR v3.4 §4.1 — cek & normalisasi periode demand lama (tgl ≠ 1) sebelum/sesudah deploy."""
from datetime import date
from types import SimpleNamespace

import pytest

from app.scripts.normalize_demand_periods import plan_normalization, run_normalization


def _row(rid, code, period, session="u1"):
    return SimpleNamespace(id=rid, product_code=code, period=period, upload_session_id=session)


def test_plan_geser_ke_awal_bulan_tanpa_bentrok():
    rows = [_row(1, "A", date(2024, 1, 24)), _row(2, "A", date(2024, 2, 24)), _row(3, "B", date(2024, 1, 24))]
    fixes, conflicts = plan_normalization(rows, existing=set())
    assert [(r.id, p) for r, p in fixes] == [(1, date(2024, 1, 1)), (2, date(2024, 2, 1)), (3, date(2024, 1, 1))]
    assert conflicts == []


def test_plan_bentrok_tidak_disentuh():
    """Dua baris satu upload & produk jatuh di bulan sama, atau bulan itu sudah punya baris tgl 1
    di upload yang sama → dilaporkan, tidak digeser (butuh keputusan manusia)."""
    rows = [
        _row(1, "A", date(2026, 1, 24)), _row(2, "A", date(2026, 1, 25)),  # 'Jan-24' & 'Jan-25'
        _row(3, "B", date(2024, 3, 24)),
        _row(4, "C", date(2024, 5, 24), session="u2"),
    ]
    existing = {("u1", "B", date(2024, 3, 1))}
    fixes, conflicts = plan_normalization(rows, existing)
    assert [r.id for r, _ in fixes] == [4]
    assert sorted(r.id for r in conflicts) == [1, 2, 3]


class FakeRepo:
    def __init__(self, rows, existing=()):
        self.rows = rows
        self.existing = set(existing)
        self.flushed = False

    async def list_unnormalized(self):
        return [r for r in self.rows if r.period.day != 1]

    async def normalized_keys(self):
        return self.existing

    async def flush(self):
        self.flushed = True


@pytest.mark.asyncio
async def test_run_laporan_saja_tidak_mengubah():
    rows = [_row(1, "A", date(2024, 1, 24))]
    report = await run_normalization(FakeRepo(rows), apply=False)
    assert report == {"unnormalized": 1, "fixable": 1, "conflicts": 0, "applied": 0}
    assert rows[0].period == date(2024, 1, 24)


@pytest.mark.asyncio
async def test_run_apply_menggeser_yang_aman():
    rows = [_row(1, "A", date(2024, 1, 24)), _row(2, "A", date(2026, 1, 24)), _row(3, "A", date(2026, 1, 25))]
    repo = FakeRepo(rows)
    report = await run_normalization(repo, apply=True)
    assert report == {"unnormalized": 3, "fixable": 1, "conflicts": 2, "applied": 1}
    assert [r.period for r in rows] == [date(2024, 1, 1), date(2026, 1, 24), date(2026, 1, 25)]
    assert repo.flushed
