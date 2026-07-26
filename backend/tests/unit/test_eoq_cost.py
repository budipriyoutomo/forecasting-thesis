"""
Fase 5 v3.0 — EOQ dinamis & total biaya. Angka diverifikasi manual (AGENTS.md §3).
"""
from decimal import Decimal

import pytest

from app.services.reorder_service import (
    compute_eoq,
    compute_savings_pct,
    compute_tic,
    round_to_moq,
)


def test_eoq_konstan_biaya_simpan_dominan_pesan_tiap_periode():
    # demand [10,10,10,10], S=5, H=1.
    #   n=1: order 40, inv akhir 30,20,10,0 → holding=60 ; TC=5+60=65
    #   n=2: 2 order @20 → inv 10,0,10,0 → holding=20 ; TC=10+20=30
    #   n=4: 4 order @10 → inv 0 tiap periode → holding=0 ; TC=20 → menang
    eoq = compute_eoq([10, 10, 10, 10], ordering_cost=5, holding_cost=1)
    assert eoq.n == 4
    assert float(eoq.eoq_qty) == pytest.approx(10.0)  # 40/4
    assert float(eoq.total_cost) == pytest.approx(20.0)


def test_eoq_biaya_pesan_dominan_pesan_sekali():
    # S besar (100) >> H (1) → satu kali pesan paling murah
    eoq = compute_eoq([10, 10, 10, 10], ordering_cost=100, holding_cost=1)
    assert eoq.n == 1
    assert float(eoq.eoq_qty) == pytest.approx(40.0)


def test_eoq_demand_kosong_aman():
    eoq = compute_eoq([], ordering_cost=5, holding_cost=1)
    assert eoq.n == 1
    assert float(eoq.eoq_qty) == 0.0


def test_round_to_moq_membulatkan_ke_atas():
    assert round_to_moq(87, 500) == Decimal("500")
    assert round_to_moq(1200, 500) == Decimal("1500")
    assert round_to_moq(1000, 500) == Decimal("1000")


def test_round_to_moq_nol_kembalikan_apa_adanya():
    assert round_to_moq(87.4, 0) == Decimal("87.4")


def test_tic_penjumlahan():
    assert compute_tic(120, 80) == Decimal("200")


def test_savings_pct():
    # (1000-750)/1000*100 = 25%
    assert float(compute_savings_pct(1000, 750)) == pytest.approx(25.0)


def test_savings_pct_actual_nol_aman():
    assert compute_savings_pct(0, 100) == Decimal("0")
