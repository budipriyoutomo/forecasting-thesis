"""Fase 5 v3.0 — breakdown BOM, standar pemakaian & buffer stock (fungsi murni)."""
import pytest

from app.services.bom_service import (
    BomLine,
    breakdown_requirements,
    compute_buffer_stock,
    compute_standard_usage,
)


def test_breakdown_akumulasi_per_material():
    # produk P1 forecast 100, P2 forecast 50.
    # BOM: P1 butuh 2×M1 + 1×M2 ; P2 butuh 3×M1.
    #   M1 = 100*2 + 50*3 = 350 ; M2 = 100*1 = 100
    lines = [
        BomLine("P1", "M1", 2),
        BomLine("P1", "M2", 1),
        BomLine("P2", "M1", 3),
    ]
    req = breakdown_requirements({"P1": 100, "P2": 50}, lines)
    assert req["M1"] == pytest.approx(350)
    assert req["M2"] == pytest.approx(100)


def test_breakdown_abaikan_produk_tanpa_forecast():
    lines = [BomLine("P1", "M1", 2), BomLine("P2", "M1", 5)]
    req = breakdown_requirements({"P1": 10}, lines)  # P2 tak ada forecast
    assert req == {"M1": pytest.approx(20)}


def test_standard_usage():
    # Output 1000 unit × BOM 2/unit = 2000
    assert compute_standard_usage(1000, 2) == pytest.approx(2000)


def test_buffer_stock_positif():
    # standar 2000, aktual 1800 → buffer qty 200, pct 10%
    qty, pct = compute_buffer_stock(2000, 1800)
    assert qty == pytest.approx(200)
    assert pct == pytest.approx(10.0)


def test_buffer_stock_aktual_lebih_besar_qty_nol():
    qty, pct = compute_buffer_stock(1000, 1200)
    assert qty == 0.0
    assert pct == pytest.approx(-20.0)


def test_buffer_stock_standar_nol_aman():
    qty, pct = compute_buffer_stock(0, 0)
    assert qty == 0.0
    assert pct == 0.0
