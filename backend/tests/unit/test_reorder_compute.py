"""
Fase 5 — fungsi murni compute_reorder. Angka diverifikasi manual (AGENTS.md §3:
"verifikasi manual hasil hitung sebelum dianggap benar").

Rumus (docs/ARCHITECTURE.md §4, standar inventory):
  SS  = manual_safety_stock jika diisi, else Z * σ_harian * sqrt(lead_time)
  ROP = μ_harian * lead_time + SS
  S   = order-up-to level = ROP + μ_harian * lead_time  (= 2·μ·LT + SS)
  current <= ROP      → urgent,   qty = max(MOQ, ceil(S - current))
  ROP < current <= S  → safe,     qty = 0
  current > S         → overstock, qty = 0
"""
import math
from decimal import Decimal

import pytest

from app.services.reorder_service import compute_reorder

Z = 1.65


def test_demand_stabil_lead_pendek():
    # μ=10, σ=2, LT=4 → SS=1.65*2*2=6.6 ; ROP=40+6.6=46.6 ; S=86.6 ; current 0 → urgent
    r = compute_reorder(mu=10, sigma=2, lead_time_days=4, moq=0, z=Z, manual_ss=None, current_stock=0)

    assert float(r.safety_stock) == pytest.approx(6.6)
    assert float(r.reorder_point) == pytest.approx(46.6)
    assert r.status == "urgent"
    assert r.recommended_order_qty == math.ceil(86.6)  # 87


def test_demand_volatile_safety_stock_lebih_besar():
    stabil = compute_reorder(mu=10, sigma=2, lead_time_days=4, moq=0, z=Z, manual_ss=None, current_stock=0)
    volatile = compute_reorder(mu=10, sigma=8, lead_time_days=4, moq=0, z=Z, manual_ss=None, current_stock=0)

    assert volatile.safety_stock > stabil.safety_stock
    assert float(volatile.safety_stock) == pytest.approx(1.65 * 8 * 2)  # 26.4


def test_lead_time_panjang_menaikkan_rop():
    pendek = compute_reorder(mu=5, sigma=3, lead_time_days=4, moq=0, z=Z, manual_ss=None, current_stock=0)
    panjang = compute_reorder(mu=5, sigma=3, lead_time_days=16, moq=0, z=Z, manual_ss=None, current_stock=0)

    # SS panjang = 1.65*3*sqrt(16)=1.65*3*4=19.8 ; ROP=5*16+19.8=99.8
    assert float(panjang.safety_stock) == pytest.approx(19.8)
    assert float(panjang.reorder_point) == pytest.approx(99.8)
    assert panjang.reorder_point > pendek.reorder_point


def test_moq_besar_membatasi_order_qty():
    r = compute_reorder(mu=10, sigma=2, lead_time_days=4, moq=500, z=Z, manual_ss=None, current_stock=0)

    assert r.recommended_order_qty == 500  # max(MOQ=500, 87)


def test_manual_safety_stock_override():
    r = compute_reorder(mu=10, sigma=2, lead_time_days=4, moq=0, z=Z, manual_ss=100, current_stock=0)

    assert r.safety_stock == 100
    assert float(r.reorder_point) == pytest.approx(140)  # 40 + 100


def test_status_safe_ketika_stok_di_antara_rop_dan_s():
    # ROP=46.6, S=86.6 ; current=60 → safe, qty 0
    r = compute_reorder(mu=10, sigma=2, lead_time_days=4, moq=0, z=Z, manual_ss=None, current_stock=60)

    assert r.status == "safe"
    assert r.recommended_order_qty == 0


def test_status_overstock_ketika_stok_di_atas_s():
    r = compute_reorder(mu=10, sigma=2, lead_time_days=4, moq=0, z=Z, manual_ss=None, current_stock=200)

    assert r.status == "overstock"
    assert r.recommended_order_qty == 0


def test_status_urgent_di_batas_rop():
    # current tepat = ROP (46.6) → masih urgent ; qty = ceil(S - ROP) = ceil(40) = 40
    r = compute_reorder(mu=10, sigma=2, lead_time_days=4, moq=0, z=Z, manual_ss=None, current_stock=46.6)

    assert r.status == "urgent"
    assert r.recommended_order_qty == 40


def test_hasil_bertipe_decimal_untuk_kolom_numeric():
    r = compute_reorder(mu=10, sigma=2, lead_time_days=4, moq=0, z=Z, manual_ss=None, current_stock=0)

    assert isinstance(r.safety_stock, Decimal)
    assert isinstance(r.reorder_point, Decimal)
    assert isinstance(r.recommended_order_qty, Decimal)
