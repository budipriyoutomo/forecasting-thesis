"""Standar pemakaian & buffer stock (fungsi murni) — dipakai reorder/cost.

Fase 11.1 (REVISI_V2 §3.8, Keputusan #8): buffer = rasio aktual : standar.
  waste_factor = aktual / standar
  buffer_qty   = max(0, waste_factor − 1) × kebutuhan material periode
Rumus lama `max(0, standar − aktual)` selalu 0 saat ada waste → diganti.
"""
import pytest

from app.services.bom_service import compute_buffer_qty, compute_standard_usage, compute_waste_factor


def test_standard_usage():
    # Output 1000 unit × BOM 2/unit = 2000
    assert compute_standard_usage(1000, 2) == pytest.approx(2000)


def test_waste_factor_ada_waste():
    assert compute_waste_factor(actual=1030, standard=1000) == pytest.approx(1.03)


def test_waste_factor_standar_nol_tak_terdefinisi():
    assert compute_waste_factor(actual=10, standard=0) is None


def test_buffer_qty_waste_3_persen():
    # waste 3% → buffer 3% dari kebutuhan periode 5000 = 150
    assert compute_buffer_qty(1.03, 5000) == pytest.approx(150)


def test_buffer_qty_tanpa_waste_atau_hemat_nol():
    assert compute_buffer_qty(1.0, 5000) == 0
    assert compute_buffer_qty(0.95, 5000) == 0  # pemakaian di bawah standar → tidak perlu buffer
    assert compute_buffer_qty(None, 5000) == 0  # belum ada data pemakaian
