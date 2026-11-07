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


# ── Buffer stock ikut menaikkan ROP & order-up-to (Fase 11.1) ──


def test_buffer_menaikkan_rop_dan_qty():
    tanpa = compute_reorder(mu=10, sigma=2, lead_time_days=4, moq=0, z=Z, manual_ss=None, current_stock=0)
    dengan = compute_reorder(mu=10, sigma=2, lead_time_days=4, moq=0, z=Z, manual_ss=None, current_stock=0, buffer=15)

    assert float(dengan.reorder_point) == pytest.approx(float(tanpa.reorder_point) + 15)  # 46.6 + 15
    assert dengan.recommended_order_qty == math.ceil(86.6 + 15)


# ── Fase 11.9 (v3.3): rumus ROP & kebijakan qty pesan configurable ──
#   compute_rop: standard = μ·L + SS | with_buffer = μ·L + SS + B
#   compute_order_qty (hanya bila current ≤ ROP, else 0):
#     order_up_to → max(MOQ, ceil(S − current))
#     eoq         → n × EOQ, n ≥ 1 terkecil s.d. current + n·EOQ ≥ ROP; EOQ ≤ 0 → order_up_to

from app.services.reorder_service import OrderPolicy, compute_order_qty, compute_rop  # noqa: E402


def test_compute_rop_standard_tanpa_buffer():
    assert compute_rop(mu_daily=10, lead_time_days=7, ss=20, buffer=5, formula="standard") == pytest.approx(90)


def test_compute_rop_with_buffer():
    assert compute_rop(mu_daily=10, lead_time_days=7, ss=20, buffer=5, formula="with_buffer") == pytest.approx(95)


def test_compute_rop_formula_tidak_dikenal_ditolak():
    with pytest.raises(ValueError):
        compute_rop(mu_daily=10, lead_time_days=7, ss=20, buffer=5, formula="wilson")


def test_order_qty_order_up_to_dengan_moq():
    # S − current = 160 − 40 = 120 < MOQ 200 → 200
    assert compute_order_qty("order_up_to", current=40, rop=90, order_up_to=160, eoq_qty=0, moq=200) == 200
    assert compute_order_qty("order_up_to", current=40, rop=90, order_up_to=160.2, eoq_qty=0, moq=0) == 121


def test_order_qty_eoq_satu_kali():
    # 40 + 1 × 300 ≥ 90 → 300
    assert compute_order_qty("eoq", current=40, rop=90, order_up_to=160, eoq_qty=300, moq=0) == 300


def test_order_qty_eoq_kelipatan_bila_kekurangan_besar():
    # pre −300, ROP 200 → butuh 500 → 2 × 300 = 600
    assert compute_order_qty("eoq", current=-300, rop=200, order_up_to=400, eoq_qty=300, moq=0) == 600


def test_order_qty_eoq_tepat_di_rop_tetap_pesan_satu():
    assert compute_order_qty("eoq", current=90, rop=90, order_up_to=160, eoq_qty=300, moq=0) == 300


def test_order_qty_eoq_nol_fallback_order_up_to():
    assert compute_order_qty("eoq", current=40, rop=90, order_up_to=160, eoq_qty=0, moq=0) == 120


def test_order_qty_di_atas_rop_nol():
    for policy in ("eoq", "order_up_to"):
        assert compute_order_qty(policy, current=91, rop=90, order_up_to=160, eoq_qty=300, moq=50) == 0


def test_order_qty_policy_tidak_dikenal_ditolak():
    with pytest.raises(ValueError):
        compute_order_qty("lot4lot", current=0, rop=90, order_up_to=160, eoq_qty=300, moq=0)


def test_order_policy_dataclass_memanggil_fungsi_yang_sama():
    p = OrderPolicy(policy="eoq", reorder_point=200, order_up_to=400, eoq_qty=300, moq=0)
    assert p.order_qty(-300) == compute_order_qty("eoq", -300, 200, 400, 300, 0) == 600
    assert p.order_qty(201) == 0


def test_compute_reorder_default_perilaku_lama():
    # Default (with_buffer + order_up_to) = identik dgn test_buffer_menaikkan_rop_dan_qty.
    a = compute_reorder(mu=10, sigma=0, lead_time_days=7, moq=0, z=Z, manual_ss=20, current_stock=0, buffer=5)
    b = compute_reorder(
        mu=10, sigma=0, lead_time_days=7, moq=0, z=Z, manual_ss=20, current_stock=0, buffer=5,
        formula="with_buffer", policy="order_up_to",
    )
    assert a == b
    assert float(a.reorder_point) == 95 and float(a.order_up_to_level) == 165 and float(a.recommended_order_qty) == 165


def test_compute_reorder_standard_mengabaikan_buffer_di_rop():
    r = compute_reorder(
        mu=10, sigma=0, lead_time_days=7, moq=0, z=Z, manual_ss=20, current_stock=0, buffer=5, formula="standard"
    )
    assert float(r.reorder_point) == 90  # 70 + 20
    assert float(r.order_up_to_level) == 160  # ROP + μ·L


def test_compute_reorder_policy_eoq():
    r = compute_reorder(
        mu=10, sigma=0, lead_time_days=7, moq=0, z=Z, manual_ss=20, current_stock=40, buffer=0,
        policy="eoq", eoq_qty=300,
    )
    assert r.status == "urgent" and float(r.recommended_order_qty) == 300
