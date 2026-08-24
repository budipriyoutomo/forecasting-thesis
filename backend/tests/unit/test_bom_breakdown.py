"""Standar pemakaian & buffer stock (fungsi murni) — dipakai reorder/cost."""
import pytest

from app.services.bom_service import compute_buffer_stock, compute_standard_usage


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
