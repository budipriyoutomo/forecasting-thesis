"""
Fase 11.6 — proyeksi stok material per periode & utilisasi gudang (REVISI_V2 §3.2/§3.3).

Per periode t (thesis "Capacity constraint gudang"):
  pre      = opening + receipt − usage
  order    = n × EOQ (n terkecil) bila pre < reorder level (SS + buffer), else 0
  ending   = max(0, pre + order);  shortage = max(0, −(pre + order))
  opening[t+1] = ending[t]
  utilisasi = stok ÷ kapasitas × 100% (stok awal & stok akhir)
"""
from datetime import date

import pytest

from app.services.stock_projection_service import bucket_by_period, project_stock


def test_proyeksi_tanpa_pesanan_dan_utilisasi():
    rows = project_stock(
        opening=1000, receipts=[200, 0], usage=[500, 400], eoq_qty=0, reorder_level=0, capacity=2000
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
    rows = project_stock(opening=100, receipts=[0], usage=[400], eoq_qty=300, reorder_level=200, capacity=None)
    r = rows[0]
    assert r.order_qty == 600 and r.ending_qty == 300 and r.shortage_qty == 0
    assert r.utilization_ending_pct is None and r.is_within_capacity is None


def test_shortage_tanpa_eoq():
    rows = project_stock(opening=100, receipts=[0, 0], usage=[300, 50], eoq_qty=0, reorder_level=0, capacity=500)
    assert rows[0].ending_qty == 0 and rows[0].shortage_qty == 200
    assert rows[1].opening_qty == 0 and rows[1].shortage_qty == 50


def test_melebihi_kapasitas_diflag():
    rows = project_stock(opening=1900, receipts=[500], usage=[100], eoq_qty=0, reorder_level=0, capacity=2000)
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
