"""
Pemilihan metode terbaik GLOBAL — satu metode untuk seluruh produk di run (23 Nov 2026,
permintaan user): "Pemilihan metode forecast terbaik untuk keseluruhan data / produk bukan per
produk, evaluasi pengujian peramalan pakai rata-rata seluruh produk."

`select_global_method(per_product_candidates, metrics)`:
  - metrik tiap metode = RATA-RATA MAD / MAPE / MFE (bertanda) seluruh produk,
  - aturan prioritas tetap 1) MAD, 2) MAPE, 3) |MFE| (`select_best_method`),
  - hanya metode yang berhasil di SEMUA produk yang dibandingkan (himpunan produk sama);
    bila tidak ada, metode dengan cakupan terbanyak,
  - MAPE tak terdefinisi di suatu produk → rata-rata dari produk yang terdefinisi.
"""
import math

import pytest

from app.services.forecasting.selection import aggregate_candidates, select_global_method


def _c(method, mad, mfe, mape):
    return {"method": method, "mad": mad, "mfe": mfe, "mse": 1.0, "mape": mape}


def test_rata_rata_metrik_seluruh_produk():
    rows, n = aggregate_candidates(
        [
            [_c("a", 2, 1, 10), _c("b", 4, -2, 20)],
            [_c("a", 6, -3, 30), _c("b", 4, 2, 10)],
        ]
    )
    by = {r["method"]: r for r in rows}
    assert n == 2
    assert by["a"]["mad"] == pytest.approx(4)
    assert by["a"]["mape"] == pytest.approx(20)
    assert by["a"]["mfe"] == pytest.approx(-1)  # MFE bertanda dirata-rata
    assert by["b"]["mfe"] == pytest.approx(0)
    assert by["a"]["n_products"] == 2


def test_pemenang_global_bukan_pemenang_tiap_produk():
    # a terbaik di p1 (MAD 1) tapi buruk di p2 (MAD 9) → rata-rata 5; b rata-rata 3.
    out = select_global_method(
        [
            [_c("a", 1, 0, 5), _c("b", 3, 0, 10)],
            [_c("a", 9, 0, 40), _c("b", 3, 0, 10)],
        ],
        ["mad", "mfe", "mape"],
    )
    assert out.best_method == "b"
    assert out.scope == "global"
    assert out.n_products == 2
    assert out.ranking[0]["mad"] == pytest.approx(3)
    d = out.to_dict()
    assert d["scope"] == "global" and d["n_products"] == 2
    assert "rata-rata" in out.summary.lower()
    assert "2 produk" in out.summary


def test_metode_gagal_di_sebagian_produk_tidak_dibandingkan():
    # lstm hanya berhasil di p1 (MAD sangat kecil) → tak adil dibandingkan; dikeluarkan.
    out = select_global_method(
        [
            [_c("lstm", 0.1, 0, 1), _c("a", 3, 0, 10), _c("b", 4, 0, 10)],
            [_c("a", 3, 0, 10), _c("b", 4, 0, 10)],
        ],
        ["mad", "mape", "mfe"],
    )
    assert out.best_method == "a"
    assert [r["method"] for r in out.ranking] == ["a", "b"]
    assert out.excluded_methods == ["lstm"]
    assert any("lstm" in r.lower() for r in out.reasons)


def test_tanpa_metode_cakupan_penuh_pakai_cakupan_terbanyak():
    out = select_global_method(
        [
            [_c("a", 2, 0, 10), _c("b", 5, 0, 10)],
            [_c("a", 2, 0, 10)],
            [_c("b", 5, 0, 10), _c("c", 1, 0, 1)],
        ],
        ["mad"],
    )
    # cakupan a=2, b=2, c=1 → a & b dibandingkan
    assert {r["method"] for r in out.ranking} == {"a", "b"}
    assert out.best_method == "a"


def test_mape_tak_terdefinisi_dirata_dari_yang_terdefinisi():
    rows, _ = aggregate_candidates(
        [
            [_c("a", 2, 0, float("nan"))],
            [_c("a", 4, 0, 10)],
        ]
    )
    assert rows[0]["mape"] == pytest.approx(10)
    rows, _ = aggregate_candidates([[_c("a", 2, 0, math.inf)]])
    assert rows[0]["mape"] is None


def test_satu_produk_sama_dengan_pemilihan_biasa():
    out = select_global_method([[_c("a", 4, 0, 30), _c("b", 5, 0, 10)]], ["mad", "mape"])
    assert out.best_method == "a"
    assert out.n_products == 1
    assert "rata-rata" not in out.summary.lower()


def test_tanpa_produk_berhasil_error():
    with pytest.raises(ValueError):
        select_global_method([], ["mad"])
