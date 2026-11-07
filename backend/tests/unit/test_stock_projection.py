"""
Fase 11.6 — proyeksi stok material per periode & utilisasi gudang (REVISI_V2 §3.2/§3.3).

Per periode t (thesis "Capacity constraint gudang"):
  pre      = opening + receipt − usage
  order    = OrderPolicy.order_qty(pre) — sumber tunggal dgn tabel Reorder (Fase 11.9):
             bila pre ≤ ROP → n × EOQ / order-up-to sesuai kebijakan, else 0
  ending   = max(0, pre + order);  shortage = max(0, −(pre + order))
  opening[t+1] = ending[t]
  utilisasi = stok ÷ kapasitas × 100% (stok awal & stok akhir)
"""
from datetime import date

import pytest

from app.services.reorder_service import OrderPolicy
from app.services.stock_projection_service import bucket_by_period, project_stock


def test_proyeksi_tanpa_pesanan_dan_utilisasi():
    rows = project_stock(
        opening=1000, receipts=[200, 0], usage=[500, 400], policy=None, capacity=2000
    )
    assert [(r.opening_qty, r.receipt_qty, r.usage_qty, r.order_qty, r.ending_qty) for r in rows] == [
        (1000, 200, 500, 0, 700),
        (700, 0, 400, 0, 300),
    ]
    assert rows[0].utilization_opening_pct == pytest.approx(50)
    assert rows[0].utilization_ending_pct == pytest.approx(35)
    assert all(r.is_within_capacity for r in rows)


def test_pesanan_eoq_saat_di_bawah_reorder_level():
    # pre = 100 + 0 − 400 = −300 < level 200 → butuh 500 → 2 × EOQ 300 = 600
    rows = project_stock(opening=100, receipts=[0], usage=[400], policy=OrderPolicy("eoq", reorder_point=200, order_up_to=400, eoq_qty=300, moq=0), capacity=None)
    r = rows[0]
    assert r.order_qty == 600 and r.ending_qty == 300 and r.shortage_qty == 0
    assert r.utilization_ending_pct is None and r.is_within_capacity is None


def test_shortage_tanpa_eoq():
    rows = project_stock(opening=100, receipts=[0, 0], usage=[300, 50], policy=None, capacity=500)
    assert rows[0].ending_qty == 0 and rows[0].shortage_qty == 200
    assert rows[1].opening_qty == 0 and rows[1].shortage_qty == 50


def test_melebihi_kapasitas_diflag():
    rows = project_stock(opening=1900, receipts=[500], usage=[100], policy=None, capacity=2000)
    assert rows[0].ending_qty == 2300
    assert rows[0].is_within_capacity is False
    assert rows[0].utilization_ending_pct == pytest.approx(115)


def test_bucket_kedatangan_per_periode():
    periods = [date(2026, 11, 1), date(2026, 12, 1), date(2027, 1, 1)]
    receipts = [
        (date(2026, 10, 20), 50),  # sebelum periode pertama (setelah snapshot) → periode pertama
        (date(2026, 11, 15), 100),
        (date(2026, 12, 1), 30),
        (date(2027, 1, 31), 70),
        (date(2027, 3, 1), 999),  # di luar horizon → diabaikan
    ]
    assert bucket_by_period(periods, receipts) == [150, 30, 70]


def test_pesanan_order_up_to_dengan_moq():
    # pre = 100 − 400 = −300 ≤ ROP 200 → max(MOQ 100, ceil(400 − (−300))) = 700
    policy = OrderPolicy("order_up_to", reorder_point=200, order_up_to=400, eoq_qty=300, moq=100)
    r = project_stock(opening=100, receipts=[0], usage=[400], policy=policy, capacity=None)[0]
    assert r.order_qty == 700 and r.ending_qty == 400


def test_tepat_di_rop_ikut_pesan():
    # Pembanding sama dgn Reorder: current ≤ ROP → pesan (dulu proyeksi pakai < )
    policy = OrderPolicy("eoq", reorder_point=200, order_up_to=400, eoq_qty=300, moq=0)
    r = project_stock(opening=600, receipts=[0], usage=[400], policy=policy, capacity=None)[0]
    assert r.order_qty == 300


def test_override_planner_mengganti_pesanan_periode_pertama_saja():
    # Fase 11.14: qty override = keputusan "pesan sekarang" → periode 1 = override (meski stok > ROP),
    # periode berikutnya kembali ke kebijakan sistem.
    policy = OrderPolicy("eoq", reorder_point=200, order_up_to=400, eoq_qty=300, moq=0)
    rows = project_stock(opening=1000, receipts=[0, 0], usage=[100, 800], policy=policy, capacity=None,
                         first_order=50)
    assert rows[0].order_qty == 50 and rows[0].ending_qty == 950
    assert rows[1].order_qty == 300  # pre 150 ≤ ROP 200 → kebijakan sistem (1 × EOQ)


def test_override_nol_berarti_tidak_pesan_periode_pertama():
    policy = OrderPolicy("eoq", reorder_point=200, order_up_to=400, eoq_qty=300, moq=0)
    rows = project_stock(opening=100, receipts=[0], usage=[50], policy=policy, capacity=None, first_order=0)
    assert rows[0].order_qty == 0 and rows[0].ending_qty == 50
