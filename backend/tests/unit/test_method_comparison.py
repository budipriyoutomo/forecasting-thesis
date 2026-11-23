"""
CR v3.7 — perbandingan hasil forecast run PER METODE (format thesis "Part 1 = Forecast").

`build_method_comparison(results, criteria)` = fungsi murni: matriks varian × periode per
metode, tabel pengujian (MAD/MAPE/MFE) + baris Average, dan kesimpulan metode terbaik level
run. Keputusan user 23 Nov 2026 (koreksi atas CR D8/D9):
  - `run_selection` = seleksi GLOBAL (`selection.select_global_method` / `selection_analysis`
    tersimpan, scope "global") — satu sumber kebenaran dengan metode yang dipakai run.
  - D9 dihapus: tidak ada `n_products_won` / `is_product_best`; tabel varian → metode dipakai.
"""
import math
from types import SimpleNamespace

import pytest

from app.services.forecasting.method_comparison import THESIS_METHOD_ORDER, build_method_comparison
from app.services.forecasting.selection import DEFAULT_CRITERIA, select_global_method

P1, P2 = "2026-01-01", "2026-02-01"


def _cand(method, mad, mape, mfe, values=(10.0, 20.0)):
    forecast = [
        {"date": d, "value": v, "lower": v, "upper": v} for d, v in zip((P1, P2), values)
    ] if values is not None else []
    return {"method": method, "mad": mad, "mfe": mfe, "mse": 1.0, "mape": mape, "forecast": forecast}


def _result(pid, cands, status="COMPLETED", method_used=None, analysis=None, override=None, system=None):
    metrics = {"selection_analysis": analysis} if analysis else {}
    used = method_used or (cands[0]["method"] if cands else None)
    return SimpleNamespace(
        product_id=pid,
        status=status,
        candidates_evaluated=cands if status == "COMPLETED" else None,
        method_used=used if status == "COMPLETED" else None,
        metrics=metrics,
        selection_override=override,
        system_method=system or (used if status == "COMPLETED" else None),
    )


def _by(out):
    return {m["method"]: m for m in out["methods"]}


# 1 ─ Matriks varian × periode, urutan metode format thesis
def test_matriks_dua_produk_dua_metode_urutan_thesis():
    results = [
        _result("p1", [_cand("moving_average", 3, 10, 1, (5, 6)), _cand("random_forest", 2, 8, -1, (7, 8))]),
        _result("p2", [_cand("random_forest", 4, 9, 1, (1, 2)), _cand("moving_average", 5, 11, 0, (3, 4))]),
    ]
    out = build_method_comparison(results, DEFAULT_CRITERIA)

    assert THESIS_METHOD_ORDER[:5] == [
        "random_forest", "lstm", "xgboost", "moving_average", "exponential_smoothing",
    ]
    assert [m["method"] for m in out["methods"]] == ["random_forest", "moving_average"]
    assert out["periods"] == [P1, P2]
    assert out["criteria"] == ["mad", "mape", "mfe"]
    rf = _by(out)["random_forest"]
    assert rf["label"] == "Random Forest"
    assert [r["product_id"] for r in rf["rows"]] == ["p1", "p2"]  # urutan results[]
    assert rf["rows"][0] == {
        "product_id": "p1", "status": "OK", "forecast": {P1: 7.0, P2: 8.0}, "total": 15.0,
        "mad": 2.0, "mape": 8.0, "mfe": -1.0,
    }
    assert _by(out)["moving_average"]["rows"][1]["forecast"] == {P1: 3.0, P2: 4.0}


def test_metode_di_luar_urutan_thesis_di_belakang_abjad():
    results = [_result("p1", [_cand("zeta", 1, 1, 0), _cand("arima", 1, 1, 0), _cand("lstm", 1, 1, 0)])]
    out = build_method_comparison(results, DEFAULT_CRITERIA)
    assert [m["method"] for m in out["methods"]] == ["lstm", "arima", "zeta"]


# 2 ─ Average: MAD/MAPE rata-rata biasa, MFE bertanda
def test_average_mfe_bertanda():
    results = [
        _result("p1", [_cand("random_forest", 2, 10, -2)]),
        _result("p2", [_cand("random_forest", 4, 20, 2)]),
    ]
    avg = _by(build_method_comparison(results, DEFAULT_CRITERIA))["random_forest"]["average"]
    assert avg == {"mad": pytest.approx(3), "mape": pytest.approx(15), "mfe": pytest.approx(0), "n": 2, "n_total": 2}


# 3 ─ Metode gagal di 1 produk → FAILED, n = n_total − 1, ranking_basis "common"
def test_metode_gagal_di_satu_produk():
    results = [
        _result("p1", [_cand("random_forest", 2, 10, 0), _cand("lstm", 1, 5, 0)]),
        _result("p2", [_cand("random_forest", 4, 10, 0)]),
    ]
    out = build_method_comparison(results, DEFAULT_CRITERIA)
    lstm = _by(out)["lstm"]
    assert lstm["rows"][1] == {
        "product_id": "p2", "status": "FAILED", "forecast": {}, "total": None, "mad": None, "mape": None, "mfe": None,
    }
    assert lstm["average"]["n"] == 1 and lstm["average"]["n_total"] == 2
    sel = out["run_selection"]
    assert sel["ranking_basis"] == "common"
    assert sel["excluded_methods"] == ["lstm"]
    assert sel["best_method"] == "random_forest"


def test_coverage_penuh_ranking_basis_all():
    results = [
        _result("p1", [_cand("random_forest", 2, 10, 0), _cand("xgboost", 3, 5, 0)]),
        _result("p2", [_cand("random_forest", 4, 10, 0), _cand("xgboost", 3, 5, 0)]),
    ]
    sel = build_method_comparison(results, DEFAULT_CRITERIA)["run_selection"]
    assert sel["ranking_basis"] == "all"
    assert sel["n_common"] == 2
    assert sel["excluded_methods"] == []


# 4 ─ Peringkat level run = seleksi global (select_best_method atas rata-rata)
@pytest.mark.parametrize(
    "a, b, best, decided",
    [
        ((2, 50, 9), (3, 1, 0), "random_forest", "mad"),  # MAD menang
        ((3, 5, 9), (3, 9, 0), "random_forest", "mape"),  # MAD seri → MAPE
        ((3, 5, 1), (3, 5, -4), "random_forest", "mfe"),  # seri → |MFE|
    ],
)
def test_peringkat_run_sama_dengan_seleksi_global(a, b, best, decided):
    per_product = [[_cand("random_forest", *a), _cand("xgboost", *b)]]
    results = [_result("p1", per_product[0])]
    sel = build_method_comparison(results, DEFAULT_CRITERIA)["run_selection"]
    expected = select_global_method(per_product, DEFAULT_CRITERIA)

    assert sel["best_method"] == expected.best_method == best
    assert sel["decided_by"] == decided
    assert [r["method"] for r in sel["ranking"]] == [r["method"] for r in expected.ranking]
    assert sel["ranking"][0]["rank"] == 1 and {"rank_mad", "rank_mape", "rank_mfe"} <= set(sel["ranking"][0])
    assert sel["summary"] == expected.summary
    assert sel["reasons"] == expected.reasons


def test_pakai_analisis_global_tersimpan():
    """Run baru: `selection_analysis` scope global sudah tersimpan → dipakai apa adanya
    (bukan dihitung ulang), supaya 'Terbaik' = metode yang benar-benar dipakai run."""
    stored = {
        "scope": "global", "n_products": 2, "excluded_methods": [], "best_method": "xgboost",
        "criteria": ["mad", "mape", "mfe"], "decided_by": "mad", "summary": "tersimpan", "reasons": ["r"],
        "ranking": [
            {"method": "xgboost", "rank": 1, "rank_mad": 1, "rank_mape": 1, "rank_mfe": 1, "mad": 1.0, "mape": 1.0, "mfe": 0.0},
            {"method": "random_forest", "rank": 2, "rank_mad": 2, "rank_mape": 2, "rank_mfe": 1, "mad": 2.0, "mape": 2.0, "mfe": 0.0},
        ],
    }
    cands = [_cand("random_forest", 2, 2, 0), _cand("xgboost", 1, 1, 0)]
    results = [_result("p1", cands, analysis=stored), _result("p2", cands, analysis=stored)]
    sel = build_method_comparison(results, DEFAULT_CRITERIA)["run_selection"]
    assert sel["best_method"] == "xgboost"
    assert sel["summary"] == "tersimpan"
    assert [r["method"] for r in sel["ranking"]] == ["xgboost", "random_forest"]


# 5 ─ (D9 dihapus) tabel varian → metode dipakai; override planner tidak mengubah run_selection
def test_override_planner_tidak_mengubah_run_selection():
    cands = [_cand("random_forest", 2, 10, 0), _cand("xgboost", 3, 10, 0)]
    results = [
        _result("p1", cands, method_used="xgboost", system="random_forest", override=SimpleNamespace(reason="x")),
        _result("p2", cands, method_used="random_forest"),
    ]
    out = build_method_comparison(results, DEFAULT_CRITERIA)
    assert out["run_selection"]["best_method"] == "random_forest"
    assert out["product_methods"] == [
        {"product_id": "p1", "status": "COMPLETED", "system_method": "random_forest", "method_used": "xgboost", "is_overridden": True},
        {"product_id": "p2", "status": "COMPLETED", "system_method": "random_forest", "method_used": "random_forest", "is_overridden": False},
    ]
    assert "n_products_won" not in out["methods"][0]
    assert "is_product_best" not in out["methods"][0]["rows"][0]


# 6 ─ Run lama tanpa deret, mode manual, NaN/inf
def test_run_lama_tanpa_deret_no_series():
    results = [_result("p1", [_cand("random_forest", 2, 10, 1, values=None)])]
    row = _by(build_method_comparison(results, DEFAULT_CRITERIA))["random_forest"]["rows"][0]
    assert row["status"] == "NO_SERIES"
    assert row["forecast"] == {}
    assert row["total"] is None
    assert row["mad"] == 2.0  # metrik tetap diisi


def test_mode_manual_satu_metode():
    results = [_result("p1", [_cand("moving_average", 2, 10, 1)]), _result("p2", [_cand("moving_average", 4, 10, 1)])]
    out = build_method_comparison(results, DEFAULT_CRITERIA)
    assert [m["method"] for m in out["methods"]] == ["moving_average"]
    assert out["run_selection"]["best_method"] == "moving_average"
    assert out["run_selection"]["decided_by"] is None


def test_nan_inf_jadi_null():
    results = [_result("p1", [_cand("random_forest", math.nan, math.inf, -math.inf)])]
    out = build_method_comparison(results, DEFAULT_CRITERIA)
    row = _by(out)["random_forest"]["rows"][0]
    assert row["mad"] is None and row["mape"] is None and row["mfe"] is None
    assert _by(out)["random_forest"]["average"] == {"mad": None, "mape": None, "mfe": None, "n": 1, "n_total": 1}


# 7 ─ Produk gagal (INSUFFICIENT_DATA) → FAILED di semua metode, tidak ikut rata-rata
def test_produk_gagal_failed_di_semua_metode():
    results = [
        _result("p1", [_cand("random_forest", 2, 10, 0), _cand("xgboost", 3, 10, 0)]),
        _result("p2", [], status="INSUFFICIENT_DATA"),
    ]
    out = build_method_comparison(results, DEFAULT_CRITERIA)
    for m in out["methods"]:
        assert m["rows"][1]["status"] == "FAILED"
        assert m["average"]["n"] == 1 and m["average"]["n_total"] == 2
    assert _by(out)["random_forest"]["average"]["mad"] == pytest.approx(2)
    assert out["run_selection"]["ranking_basis"] == "all"  # produk gagal bukan soal coverage metode
    assert out["product_methods"][1] == {
        "product_id": "p2", "status": "INSUFFICIENT_DATA", "system_method": None, "method_used": None, "is_overridden": False,
    }


def test_tanpa_hasil_berhasil_run_selection_null():
    out = build_method_comparison([_result("p1", [], status="INSUFFICIENT_DATA")], DEFAULT_CRITERIA)
    assert out["methods"] == [] and out["periods"] == []
    assert out["run_selection"] is None
