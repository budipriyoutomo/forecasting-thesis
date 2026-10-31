"""
Fase 11.4 — EOQ klasik thesis (REVISI_V2 §3.5, docx "Rumus thesis untuk program"):

  EOQ = √(2AS / iC)        A = demand tahunan, S = biaya pesan, i = % biaya simpan
  TC  = (A/Q)·S + (Q/2)·i·C      tahunan, C = harga material per unit
A = rata-rata kebutuhan per periode × periode per tahun (bulanan → 12).
"""
import math

import pytest

from app.services.reorder_service import (
    annual_demand,
    compute_eoq_classic,
    periods_per_year,
    suggest_holding_rate,
)


def test_eoq_klasik_verifikasi_manual():
    # A=12.000, S=250.000, i=20%, C=1.500 → EOQ = √(2·12000·250000 / 300) = √20.000.000 ≈ 4472,14
    r = compute_eoq_classic(annual_demand=12_000, ordering_cost=250_000, holding_rate=0.20, unit_price=1_500)

    q = math.sqrt(2 * 12_000 * 250_000 / (0.20 * 1_500))
    assert r.eoq_qty == pytest.approx(q)
    assert r.n_orders == pytest.approx(12_000 / q)
    assert r.ordering_cost == pytest.approx(12_000 / q * 250_000)
    assert r.holding_cost == pytest.approx(q / 2 * 0.20 * 1_500)
    assert r.total_cost == pytest.approx(r.ordering_cost + r.holding_cost)
    assert r.ordering_cost == pytest.approx(r.holding_cost)  # sifat EOQ: biaya pesan = biaya simpan


def test_eoq_klasik_tanpa_demand():
    r = compute_eoq_classic(annual_demand=0, ordering_cost=250_000, holding_rate=0.2, unit_price=1_500)
    assert r.eoq_qty == 0 and r.total_cost == 0


@pytest.mark.parametrize("rate,price", [(0, 1500), (0.2, 0), (None, 1500), (0.2, None)])
def test_eoq_klasik_tanpa_i_atau_c_ditolak(rate, price):
    with pytest.raises(ValueError):
        compute_eoq_classic(annual_demand=100, ordering_cost=1, holding_rate=rate, unit_price=price)


def test_periods_per_year():
    assert periods_per_year(31) == 12  # bulanan
    assert periods_per_year(28) == 12
    assert periods_per_year(7) == pytest.approx(365 / 7)
    assert periods_per_year(1) == 365


def test_annual_demand_dari_horizon():
    # forecast 3 bulan: 900, 1000, 1100 → rata-rata 1000/bulan × 12
    assert annual_demand([900, 1000, 1100], 31) == pytest.approx(12_000)
    assert annual_demand([], 31) == 0


def test_suggest_holding_rate():
    # Σ biaya simpan tahunan Rp 95.332.848 ÷ rata-rata nilai persediaan Rp 476.664.240 = 20%
    assert suggest_holding_rate(95_332_848, 476_664_240) == pytest.approx(20.0)
    assert suggest_holding_rate(1, 0) is None
