"""
Fase 11.0 — konversi satuan periode → harian untuk SS/ROP (docs/REVISI_V2.md §3.7).

Thesis: SS = Z · STD_harian · √L, L dalam hari. Deret forecast per PERIODE
(bulanan di data thesis) harus dikonversi dulu:
  μ_d = μ_p / days_in_period
  σ_d = σ_p / √days_in_period   (asumsi demand harian independen)
Z diturunkan dari SERVICE_LEVEL_PCT (95 → 1.6449, 99 → 2.3263).
"""
import math

import pytest

from app.services.reorder_service import (
    compute_reorder,
    days_in_period,
    period_to_daily,
    z_from_service_level,
)


def test_period_to_daily_bulanan():
    mu_d, sigma_d = period_to_daily(mu=300, sigma=60, days=30)
    assert mu_d == pytest.approx(10)
    assert sigma_d == pytest.approx(60 / math.sqrt(30))


def test_period_to_daily_harian_tidak_berubah():
    assert period_to_daily(mu=10, sigma=2, days=1) == pytest.approx((10, 2))


def test_period_to_daily_days_nol_ditolak():
    with pytest.raises(ValueError):
        period_to_daily(mu=10, sigma=2, days=0)


def test_days_in_period_dari_tanggal_bulanan():
    dates = ["2026-01-01", "2026-02-01", "2026-03-01", "2026-04-01"]
    assert days_in_period(dates) == pytest.approx(31)  # median selisih (31, 28, 31)


def test_days_in_period_mingguan():
    assert days_in_period(["2026-01-05", "2026-01-12", "2026-01-19"]) == pytest.approx(7)


def test_days_in_period_fallback_satu_hari():
    assert days_in_period([]) == 1
    assert days_in_period(["2026-01-01"]) == 1
    assert days_in_period([None, None]) == 1


def test_z_from_service_level():
    assert z_from_service_level(95) == pytest.approx(1.6449, abs=1e-4)
    assert z_from_service_level(99) == pytest.approx(2.3263, abs=1e-4)


@pytest.mark.parametrize("pct", [0, 50, 100, 120])
def test_z_from_service_level_di_luar_rentang_ditolak(pct):
    with pytest.raises(ValueError):
        z_from_service_level(pct)


def test_rop_bulanan_lead_7_hari_bukan_30x():
    # Kasus wajib §3.7: μ_bulanan=300, σ_bulanan=60, LT=7 hari, data 30 hari/periode.
    mu_d, sigma_d = period_to_daily(mu=300, sigma=60, days=30)
    z = 1.65
    r = compute_reorder(mu=mu_d, sigma=sigma_d, lead_time_days=7, moq=0, z=z, manual_ss=None, current_stock=0)

    ss = z * (60 / math.sqrt(30)) * math.sqrt(7)  # ≈ 47.82
    assert float(r.safety_stock) == pytest.approx(ss, abs=1e-3)
    assert float(r.reorder_point) == pytest.approx(300 * 7 / 30 + ss, abs=1e-3)  # ≈ 117.82, bukan 2100+
    # order-up-to = ROP + μ_d·LT = 70 + 117.82 → qty = ceil(187.82) = 188
    assert r.recommended_order_qty == math.ceil(70 + 300 * 7 / 30 + ss)
