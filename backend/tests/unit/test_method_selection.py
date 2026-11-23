"""
Test pemilihan metode terbaik otomatis (23 Nov 2026, membalik Fase 11.15 atas permintaan user).

Fungsi murni `select_best_method(candidates, metrics)` — URUTAN PRIORITAS pengujian
(keputusan user 23 Nov 2026): 1) MAD, 2) MAPE, 3) MFE (|MFE|).
  - metode dengan MAD terkecil menang; MAPE hanya menentukan bila MAD seri, lalu |MFE|,
  - metrik yang tidak dicentang di Pengaturan Forecast dilewati (urutan prioritas tetap),
  - nilai tak terdefinisi (NaN/inf/None) → kalah di metrik itu,
  - peringkat per metrik tetap dicatat (informasi), plus analisis bahasa natural.
"""
import math

from app.services.forecasting.selection import select_best_method


def _c(method, mad, mfe, mape, mse=1.0):
    return {"method": method, "mad": mad, "mfe": mfe, "mse": mse, "mape": mape}


def test_urutan_prioritas_mad_mape_mfe():
    out = select_best_method(
        [_c("moving_average", 10, 4, 20), _c("xgboost", 5, 1, 8), _c("random_forest", 7, -2, 12)],
        ["mad", "mfe", "mape"],
    )
    assert out.criteria == ["mad", "mape", "mfe"]
    assert out.best_method == "xgboost"
    assert [r["method"] for r in out.ranking] == ["xgboost", "random_forest", "moving_average"]
    assert [r["rank"] for r in out.ranking] == [1, 2, 3]
    assert out.decided_by == "mad"


def test_mad_terkecil_menang_walau_mape_dan_mfe_lebih_buruk():
    # a: MAD terbaik tapi MAPE & bias terburuk → tetap menang (MAD prioritas 1).
    out = select_best_method([_c("a", 4, 9, 30), _c("b", 5, 1, 10), _c("c", 6, 0, 12)], ["mad", "mfe", "mape"])
    assert out.best_method == "a"
    assert out.decided_by == "mad"


def test_mad_seri_diputus_mape():
    out = select_best_method([_c("a", 5, 0, 12), _c("b", 5, 3, 10)], ["mad", "mfe", "mape"])
    assert out.best_method == "b"
    assert out.decided_by == "mape"


def test_mad_dan_mape_seri_diputus_mfe_absolut():
    out = select_best_method([_c("a", 5, 3, 10), _c("b", 5, -1, 10)], ["mad", "mfe", "mape"])
    assert out.best_method == "b"  # |−1| < |3|
    assert out.decided_by == "mfe"


def test_seri_sangat_tipis_dianggap_seri():
    # Selisih di bawah presisi simpan (Numeric 6 desimal) tidak menentukan.
    out = select_best_method([_c("a", 5.0000001, 0, 12), _c("b", 5.0000002, 0, 10)], ["mad", "mape"])
    assert out.best_method == "b"
    assert out.decided_by == "mape"


def test_semua_seri_diputus_nama_metode():
    out = select_best_method([_c("b", 5, 1, 10), _c("a", 5, 1, 10)], ["mad", "mfe", "mape"])
    assert out.best_method == "a"
    assert out.decided_by is None


def test_metrik_tidak_dicentang_dilewati():
    out = select_best_method([_c("a", 4, 0, 30), _c("b", 5, 0, 10)], ["mape", "mfe"])
    assert out.criteria == ["mape", "mfe"]
    assert out.best_method == "b"


def test_metrik_seri_mendapat_peringkat_sama():
    out = select_best_method([_c("a", 5, 0, 10), _c("b", 5, 0, 12), _c("c", 6, 0, 14)], ["mad"])
    ranks = {r["method"]: r["rank_mad"] for r in out.ranking}
    assert ranks == {"a": 1, "b": 1, "c": 3}


def test_metrik_tak_terdefinisi_kalah():
    out = select_best_method(
        [_c("a", float("nan"), 0, 5), _c("b", 6, 0, math.inf), _c("c", 7, 0, 30)],
        ["mad", "mape"],
    )
    assert out.best_method == "b"
    ranks = {r["method"]: (r["rank_mad"], r["rank_mape"]) for r in out.ranking}
    assert ranks["a"] == (3, 1)
    assert ranks["b"] == (1, 3)


def test_satu_kandidat_tetap_terpilih():
    out = select_best_method([_c("a", 5, 0, 10)], ["mad", "mfe", "mape"])
    assert out.best_method == "a"
    assert "satu-satunya" in out.summary.lower()


def test_analisis_menjelaskan_prioritas_dan_alasan():
    out = select_best_method(
        [_c("moving_average", 10, 4, 20), _c("xgboost", 5, 1, 8), _c("random_forest", 7, -2, 12)],
        ["mad", "mfe", "mape"],
    )
    text = " ".join([out.summary, *out.reasons]).lower()
    assert "1) mad, 2) mape, 3) mfe" in text
    assert "xgboost" in text and "random forest" in text  # pembanding terdekat disebut
    assert "sangat baik" in text  # label Lewis MAPE 8%


def test_analisis_menyebut_metrik_penentu_saat_mad_seri():
    out = select_best_method([_c("a", 5, 0, 12), _c("b", 5, 3, 10)], ["mad", "mfe", "mape"])
    assert "mad seri" in out.summary.lower()
    assert "mape" in out.summary.lower()


def test_analisis_mencatat_metrik_prioritas_rendah_yang_kalah():
    out = select_best_method([_c("a", 4, 9, 30), _c("b", 5, 1, 10)], ["mad", "mfe", "mape"])
    text = " ".join(out.reasons).lower()
    assert "tidak mengubah keputusan" in text


def test_to_dict_bisa_disimpan_ke_jsonb():
    import json

    out = select_best_method([_c("a", 5, 0, math.inf), _c("b", 6, 0, 30)], ["mad", "mape"])
    payload = json.loads(json.dumps(out.to_dict(), allow_nan=False))  # tanpa NaN/inf
    assert payload["best_method"] == "a"
    assert payload["decided_by"] == "mad"
    assert "rank_total" not in payload["ranking"][0]


def test_metrik_kosong_pakai_default():
    out = select_best_method([_c("a", 5, 0, 10), _c("b", 4, 0, 9)], [])
    assert out.criteria == ["mad", "mape", "mfe"]
    assert out.best_method == "b"
