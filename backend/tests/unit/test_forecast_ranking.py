"""
Fase 11.2a — 3 kolom ranking kandidat (Keputusan #6, docs/REVISI_V2.md §6.1).

`rank_candidates` menambah `rank_mad`, `rank_mfe` (berdasarkan |MFE|) dan `rank_mape`
ke tiap baris `candidates_evaluated`. Peringkat 1 = terbaik (nilai terkecil).
Seri → peringkat sama, berikutnya dilompati (1, 1, 3). Metrik tak terdefinisi
(None/NaN) → peringkat None, tidak ikut diperingkat.
"""
import math

from app.services.forecasting.forecast_service import rank_candidates


def _c(method, mad, mfe, mape):
    return {"method": method, "mad": mad, "mfe": mfe, "mse": 0.0, "mape": mape, "mase": None}


def test_tiga_peringkat_independen():
    ranked = rank_candidates(
        [
            _c("moving_average", mad=12.5, mfe=-2.1, mape=11.42),
            _c("xgboost", mad=8.2, mfe=4.0, mape=8.2),
            _c("random_forest", mad=9.9, mfe=1.2, mape=9.75),
        ]
    )
    by = {c["method"]: c for c in ranked}

    assert [by[m]["rank_mad"] for m in ("xgboost", "random_forest", "moving_average")] == [1, 2, 3]
    assert [by[m]["rank_mape"] for m in ("xgboost", "random_forest", "moving_average")] == [1, 2, 3]
    # |MFE|: rf 1.2 < ma 2.1 < xgb 4.0 → bias terkecil menang, tanda diabaikan
    assert [by[m]["rank_mfe"] for m in ("random_forest", "moving_average", "xgboost")] == [1, 2, 3]


def test_urutan_dan_isi_asli_dipertahankan():
    rows = [_c("a", 2, 1, 5), _c("b", 1, 1, 4)]
    ranked = rank_candidates(rows)

    assert [c["method"] for c in ranked] == ["a", "b"]
    assert ranked[0]["mad"] == 2 and ranked[0]["mase"] is None
    assert "rank_mad" not in rows[0]  # input tidak dimutasi


def test_seri_mendapat_peringkat_sama():
    ranked = rank_candidates([_c("a", 5, 1, 10), _c("b", 5, -1, 10), _c("c", 7, 3, 20)])

    assert [c["rank_mad"] for c in ranked] == [1, 1, 3]
    assert [c["rank_mfe"] for c in ranked] == [1, 1, 3]  # |1| == |-1|


def test_metrik_tak_terdefinisi_tanpa_peringkat():
    ranked = rank_candidates([_c("a", 5, 1, math.inf), _c("b", 3, None, float("nan")), _c("c", 4, 2, 9)])

    assert [c["rank_mape"] for c in ranked] == [None, None, 1]
    assert [c["rank_mfe"] for c in ranked] == [1, None, 2]
    assert [c["rank_mad"] for c in ranked] == [3, 1, 2]


def test_kosong():
    assert rank_candidates([]) == []
