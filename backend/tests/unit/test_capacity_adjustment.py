"""
Fase 11.17 — fungsi murni loop kapasitas gudang → adjust SS & Buffer
(RECONCILIATION.md §"Loop Validasi Kapasitas Gudang → Adjust SS & Buffer").
"""
from datetime import date
from types import SimpleNamespace

import pytest

from app.services.capacity_adjustment_service import (
    OVERFLOW_CAUSES,
    SERVICE_LEVEL_FLOOR,
    active_adjustments,
    classify_overflow_cause,
    cut_buffers,
    effective_service_level,
    group_overflow,
    next_service_level,
)

P1, P2 = date(2026, 1, 1), date(2026, 2, 1)


@pytest.mark.parametrize(
    "current, expected",
    [(99, 98), (98, 97), (97, 95), (95, 92.5), (92.5, 90), (96, 95), (99.5, 99), (91, 90), (90, None), (85, None)],
)
def test_anak_tangga_service_level_berikutnya(current, expected):
    assert next_service_level(current) == expected


def test_batas_bawah_service_level_90():
    assert SERVICE_LEVEL_FLOOR == 90.0


def _row(mid, period, ending, capacity, order=0.0, scenario="proposed"):
    return SimpleNamespace(
        material_id=mid, period=period, ending_qty=ending, capacity_qty=capacity,
        order_qty=order, receipt_qty=None, scenario=scenario,
    )


def test_kelebihan_per_grup_dari_total_stok_akhir_terbesar():
    group_of = {"m1": "cap", "m2": "cap", "m3": "preform"}
    capacity = {"cap": 1000.0, "preform": 500.0}
    rows = [
        _row("m1", P1, 600, 1000), _row("m2", P1, 500, 1000),  # cap P1: 1100 → +100
        _row("m1", P2, 700, 1000), _row("m2", P2, 450, 1000),  # cap P2: 1150 → +150 (terbesar)
        _row("m3", P1, 400, 500), _row("m3", P2, 500, 500),  # preform muat (= kapasitas)
        _row("m1", P1, 9999, 1000, scenario="baseline"),  # baseline tidak dihitung
    ]
    assert group_overflow(rows, group_of, capacity) == {"cap": pytest.approx(150)}


def test_kelebihan_abaikan_material_tanpa_grup_atau_kapasitas():
    rows = [_row("m1", P1, 5000, None), _row("m2", P1, 5000, None)]
    assert group_overflow(rows, {"m1": None, "m2": "bottle"}, {}) == {}


def test_potong_buffer_proporsional():
    assert cut_buffers({"a": 100.0, "b": 300.0}, 200) == {"a": pytest.approx(50), "b": pytest.approx(150)}


def test_potong_buffer_kelebihan_melebihi_total_jadi_nol():
    assert cut_buffers({"a": 100.0, "b": 300.0}, 1000) == {"a": 0.0, "b": 0.0}


def test_potong_buffer_tanpa_buffer_tidak_berubah():
    assert cut_buffers({"a": 0.0}, 50) == {"a": 0.0}


def test_service_level_efektif_dari_ss():
    # SS = z · σ_d·√L → α = Φ(SS ÷ σ_d·√L)
    assert effective_service_level(1.644854 * 10, 10) == pytest.approx(95, abs=1e-3)
    assert effective_service_level(0, 10) == pytest.approx(50)
    assert effective_service_level(10, 0) is None


def test_penyebab_overload_stok_awal_bila_belum_pernah_pesan():
    rows = [_row("m1", P1, 5000, 1000)]
    assert classify_overflow_cause(rows, {"m1": "cap"}, "cap", 1000.0, moq={}) == "opening_stock"


def test_penyebab_kedatangan_terjadwal_dihapus():
    # 20 Nov 2026: kedatangan = pesanan hasil ROP, tidak ada lagi kedatangan manual
    assert OVERFLOW_CAUSES == ("opening_stock", "moq", "cycle_stock")


def test_penyebab_overload_moq():
    rows = [_row("m1", P1, 1500, 1000, order=1400)]
    assert classify_overflow_cause(rows, {"m1": "cap"}, "cap", 1000.0, moq={"m1": 1400.0}) == "moq"


def test_penyebab_overload_cycle_stock():
    rows = [_row("m1", P1, 1500, 1000, order=900)]
    assert classify_overflow_cause(rows, {"m1": "cap"}, "cap", 1000.0, moq={"m1": 0.0}) == "cycle_stock"


def _adj(mid, source, minutes, **kw):
    return SimpleNamespace(material_id=mid, source=source, created_at=minutes, **kw)


def test_adjust_berlaku_terbaru_per_material_reset_menghapus():
    rows = [
        _adj("m1", "suggested", 1, safety_stock=10, buffer_stock=5, service_level_pct=97),
        _adj("m1", "custom", 2, safety_stock=8, buffer_stock=5, service_level_pct=None),
        _adj("m2", "custom", 1, safety_stock=3, buffer_stock=1, service_level_pct=None),
        _adj("m2", "reset", 3, safety_stock=None, buffer_stock=None, service_level_pct=None),
    ]
    active = active_adjustments(rows)
    assert set(active) == {"m1"}
    assert active["m1"].source == "custom" and active["m1"].safety_stock == 8
