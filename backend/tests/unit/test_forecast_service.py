"""
Test orkestrasi forecast_service — mode otomatis (semua metode → terbaik dipilih dari pengujian, 23 Nov 2026) vs manual
(AGENTS.md §5, docs/ARCHITECTURE.md §6.1). Tidak ada lagi klasifikasi kuadran.
"""
import pytest

from app.services.forecasting.forecast_service import run_forecast_for_product
from app.utils.exceptions import UnsupportedForecastMethodError

_ACTIVE = {"moving_average", "exponential_smoothing", "random_forest", "xgboost"}


def test_auto_mode_memilih_metode_terbaik(smooth_df):
    """23 Nov 2026 (membalik Fase 11.15): mode otomatis memilih metode terbaik dari pengujian."""
    record = run_forecast_for_product(smooth_df, horizon=7, requested_method=None)

    assert record.status == "COMPLETED"
    assert record.selection_mode == "auto"
    # candidates_evaluated menyimpan SEMUA kandidat yang berhasil (lstm auto-excluded, TF absen)
    assert {c["method"] for c in record.candidates_evaluated} == _ACTIVE
    assert record.method_used in _ACTIVE
    assert len(record.forecast) == 7
    best = next(c for c in record.candidates_evaluated if c["method"] == record.method_used)
    assert record.mad == best["mad"] and record.mape == best["mape"]
    assert best["rank"] == 1


def test_auto_mode_kandidat_membawa_deret_forecast_dan_penjelasan(smooth_df):
    """Deret forecast tiap kandidat tetap disimpan supaya planner bisa mengganti metode."""
    record = run_forecast_for_product(smooth_df, horizon=7)

    for c in record.candidates_evaluated:
        assert len(c["forecast"]) == 7
        assert {"date", "value", "lower", "upper"} <= set(c["forecast"][0])
        assert "interpretasi mape" in c["explanation"].lower()
        for key in ("mad", "mfe", "mse", "mape"):
            assert c[key] is not None


def test_auto_mode_kandidat_membawa_peringkat(smooth_df):
    record = run_forecast_for_product(smooth_df, horizon=7)

    ranks = sorted(c["rank"] for c in record.candidates_evaluated)
    assert ranks == list(range(1, len(_ACTIVE) + 1))
    for c in record.candidates_evaluated:
        assert {"rank_mad", "rank_mfe", "rank_mape"} <= set(c)
        assert "rank_total" not in c  # prioritas MAD → MAPE → MFE, bukan jumlah peringkat


def test_auto_mode_menyertakan_analisis_pemilihan(smooth_df):
    record = run_forecast_for_product(smooth_df, horizon=7)

    analysis = record.selection_analysis
    assert analysis["best_method"] == record.method_used
    assert analysis["criteria"] == ["mad", "mape", "mfe"]  # urutan prioritas (23 Nov 2026)
    assert analysis["reasons"]
    assert "terbaik" in record.explanation.lower()


def test_auto_mode_default_memilih_mad_terkecil(smooth_df):
    record = run_forecast_for_product(smooth_df, horizon=7)

    assert record.mad == min(c["mad"] for c in record.candidates_evaluated)


def test_auto_mode_kriteria_mengikuti_metrik_pengujian(smooth_df):
    record = run_forecast_for_product(smooth_df, horizon=7, selection_metrics=["mape"])

    assert record.selection_analysis["criteria"] == ["mape"]
    best_mape = min(c["mape"] for c in record.candidates_evaluated)
    assert record.mape == best_mape


def test_manual_mode_memaksa_metode(smooth_df):
    record = run_forecast_for_product(smooth_df, horizon=7, requested_method="moving_average")

    assert record.status == "COMPLETED"
    assert record.selection_mode == "manual"
    assert record.method_used == "moving_average"
    assert len(record.candidates_evaluated) == 1


def test_manual_mode_metode_tak_dikenal_error(smooth_df):
    with pytest.raises(UnsupportedForecastMethodError):
        run_forecast_for_product(smooth_df, horizon=7, requested_method="prophet")


def test_manual_gagal_tidak_fallback(smooth_df):
    # LSTM tanpa TensorFlow → fungsi raise. Mode manual TIDAK fallback (AGENTS.md §5/#14):
    # harus MODEL_SELECTION_FAILED, bukan diam-diam ganti metode lain.
    import importlib.util

    if importlib.util.find_spec("tensorflow") is not None:
        pytest.skip("TensorFlow terpasang — LSTM tidak gagal, skenario tak berlaku")
    record = run_forecast_for_product(smooth_df, horizon=5, requested_method="lstm")
    assert record.status == "MODEL_SELECTION_FAILED"
    assert record.selection_mode == "manual"
    assert record.method_used == "lstm"


def test_insufficient_data_status(too_short_df):
    record = run_forecast_for_product(too_short_df, horizon=7, requested_method=None)
    assert record.status == "INSUFFICIENT_DATA"


def test_manual_mode_explanation_tidak_mengaku_membandingkan(smooth_df):
    """Mode manual tidak membandingkan apa pun — jangan tempel narasi perbandingan."""
    record = run_forecast_for_product(smooth_df, horizon=7, requested_method="moving_average")

    assert record.explanation
    assert "dibandingkan" not in record.explanation.lower()


def test_manual_mode_kandidat_membawa_deret_forecast(smooth_df):
    record = run_forecast_for_product(smooth_df, horizon=7, requested_method="moving_average")

    assert len(record.candidates_evaluated[0]["forecast"]) == 7
    assert len(record.forecast) == 7


# ── Metode aktif dari master data (Fase 11.2a) ──


def test_auto_mode_hanya_metode_aktif(smooth_df):
    record = run_forecast_for_product(smooth_df, horizon=7, enabled_methods={"moving_average", "xgboost"})

    assert {c["method"] for c in record.candidates_evaluated} == {"moving_average", "xgboost"}


def test_manual_mode_metode_nonaktif_ditolak(smooth_df):
    with pytest.raises(UnsupportedForecastMethodError):
        run_forecast_for_product(
            smooth_df, horizon=7, requested_method="xgboost", enabled_methods={"moving_average"}
        )


# ── Opsi engine, feature importance, label MAPE (Fase 11.2) ──


def _monthly(values):
    import pandas as pd

    dates = pd.date_range("2024-01-01", periods=len(values), freq="MS")
    return pd.DataFrame({"date": dates.astype(str), "quantity": values})


def test_opsi_engine_diteruskan_ke_engine():
    from app.services.forecasting.types import EngineOptions

    record = run_forecast_for_product(
        _monthly([10 + (i % 4) for i in range(20)]),
        horizon=3,
        requested_method="exponential_smoothing",
        options=EngineOptions(es_alpha_grid=(0.8,)),
    )
    assert record.hyperparameters["alpha"] == 0.8


def test_feature_importance_pemenang_ml_tersimpan():
    record = run_forecast_for_product(
        _monthly([10 + (i % 4) * 3 for i in range(24)]), horizon=3, requested_method="random_forest"
    )
    assert "lag_1" in record.feature_importance
    assert record.hyperparameters["grid_search"] is False


def test_kandidat_otomatis_membawa_feature_importance():
    record = run_forecast_for_product(_monthly([10 + (i % 4) * 3 for i in range(24)]), horizon=3)
    rf = next(c for c in record.candidates_evaluated if c["method"] == "random_forest")
    ma = next(c for c in record.candidates_evaluated if c["method"] == "moving_average")
    assert rf["feature_importance"]
    assert ma["feature_importance"] is None


def test_explanation_menyertakan_interpretasi_mape():
    record = run_forecast_for_product(
        _monthly([10 + (i % 4) for i in range(20)]), horizon=3, requested_method="moving_average"
    )
    assert "interpretasi mape" in record.explanation.lower()


# ── CR v3.6 §7.2 — alasan gagal per produk (status_reason) ──
def test_insufficient_data_menyertakan_alasan(too_short_df):
    record = run_forecast_for_product(too_short_df, horizon=7, requested_method=None)
    assert record.status_reason is not None
    assert "5 periode" in record.status_reason
    assert "minimal 12" in record.status_reason


def test_tanpa_histori_menyertakan_alasan():
    import pandas as pd

    record = run_forecast_for_product(pd.DataFrame(columns=["date", "quantity"]), horizon=3)
    assert record.status == "INSUFFICIENT_DATA"
    assert "Belum ada histori" in record.status_reason


def test_semua_metode_gagal_menyertakan_alasan(smooth_df, monkeypatch):
    from app.services.forecasting import registry

    def boom(df, horizon, options=None):
        raise RuntimeError("x")

    monkeypatch.setattr(registry, "MODEL_REGISTRY", {"moving_average": boom})
    record = run_forecast_for_product(smooth_df, horizon=3, enabled_methods={"moving_average"})
    assert record.status == "MODEL_SELECTION_FAILED"
    assert "Semua metode" in record.status_reason


def test_sukses_tanpa_alasan(smooth_df):
    record = run_forecast_for_product(smooth_df, horizon=3, requested_method="moving_average")
    assert record.status_reason is None


# ── 23 Nov 2026 — metode terbaik GLOBAL (rata-rata seluruh produk), bukan per produk ──
def _fake_engine(mad_by_level, fail_levels=()):
    """Engine palsu: MAD ditentukan oleh level data (nilai pertama df) → per produk beda."""
    from app.services.forecasting.types import EngineResult, ForecastPoint

    def fn(df, horizon, options=None):
        level = float(df["quantity"].iloc[0])
        if level in fail_levels:
            raise RuntimeError("gagal")
        pts = [ForecastPoint(date=f"2026-0{i + 1}-01", value=level, lower=level, upper=level) for i in range(horizon)]
        return EngineResult(forecast=pts, explanation="x", mad=mad_by_level[level], mfe=0.0, mse=1.0, mape=10.0)

    return fn


def _global_registry(monkeypatch, fail_a_at=()):
    from app.services.forecasting import registry

    monkeypatch.setattr(
        registry,
        "MODEL_REGISTRY",
        {
            "moving_average": _fake_engine({10.0: 1.0, 20.0: 9.0}, fail_levels=fail_a_at),  # rata2 5
            "xgboost": _fake_engine({10.0: 3.0, 20.0: 3.0}),  # rata2 3
        },
    )


def test_multi_produk_satu_metode_terbaik_untuk_semua(monkeypatch):
    from app.services.forecasting.forecast_service import run_forecast_for_products

    _global_registry(monkeypatch)
    records = run_forecast_for_products(
        [(_monthly([10.0] * 14), None), (_monthly([20.0] * 14), None)],
        horizon=3,
        enabled_methods={"moving_average", "xgboost"},
    )
    # p1 sendiri lebih baik dengan moving_average (MAD 1), tapi rata-rata global → xgboost.
    assert [r.method_used for r in records] == ["xgboost", "xgboost"]
    assert all(r.selection_mode == "auto" for r in records)
    assert records[0].mad == 3.0  # metrik metode yang berlaku di produk itu
    a = records[0].selection_analysis
    assert a["scope"] == "global" and a["n_products"] == 2 and a["best_method"] == "xgboost"
    # kandidat produk tetap membawa metrik produk itu, peringkat = peringkat global
    ranks = {c["method"]: c["rank"] for c in records[0].candidates_evaluated}
    assert ranks == {"xgboost": 1, "moving_average": 2}
    assert records[0].candidates_evaluated[1]["mad"] == 1.0


def test_multi_produk_metode_global_gagal_di_satu_produk_pakai_terbaik_produk(monkeypatch):
    from app.services.forecasting import registry
    from app.services.forecasting.forecast_service import run_forecast_for_products

    monkeypatch.setattr(
        registry,
        "MODEL_REGISTRY",
        {
            "moving_average": _fake_engine({10.0: 5.0, 20.0: 5.0, 30.0: 5.0}),
            "xgboost": _fake_engine({10.0: 1.0, 20.0: 1.0, 30.0: 1.0}, fail_levels=(30.0,)),
            "random_forest": _fake_engine({10.0: 2.0, 20.0: 2.0, 30.0: 2.0}),
        },
    )
    records = run_forecast_for_products(
        [(_monthly([v] * 14), None) for v in (10.0, 20.0, 30.0)],
        horizon=3,
        enabled_methods={"moving_average", "xgboost", "random_forest"},
    )
    # xgboost gagal di p3 → tak punya cakupan penuh → global = random_forest (cakupan penuh)
    assert [r.method_used for r in records] == ["random_forest"] * 3


def test_multi_produk_produk_gagal_tidak_ikut_rata_rata(monkeypatch, too_short_df):
    from app.services.forecasting.forecast_service import run_forecast_for_products

    _global_registry(monkeypatch)
    records = run_forecast_for_products(
        [(_monthly([10.0] * 14), None), (too_short_df, None)],
        horizon=3,
        enabled_methods={"moving_average", "xgboost"},
    )
    assert records[1].status == "INSUFFICIENT_DATA"
    assert records[0].method_used == "moving_average"  # hanya p1 yang dinilai
    assert records[0].selection_analysis["n_products"] == 1


def test_multi_produk_fallback_bila_metode_global_gagal_di_produk(monkeypatch):
    from app.services.forecasting import registry
    from app.services.forecasting.forecast_service import run_forecast_for_products

    monkeypatch.setattr(
        registry,
        "MODEL_REGISTRY",
        {
            # cakupan sama (2 dari 3) → keduanya dibandingkan; moving_average terbaik
            "moving_average": _fake_engine({10.0: 1.0, 20.0: 1.0, 30.0: 1.0}, fail_levels=(30.0,)),
            "xgboost": _fake_engine({10.0: 2.0, 20.0: 2.0, 30.0: 2.0}, fail_levels=(10.0,)),
        },
    )
    records = run_forecast_for_products(
        [(_monthly([v] * 14), None) for v in (10.0, 20.0, 30.0)],
        horizon=3,
        enabled_methods={"moving_average", "xgboost"},
    )
    assert [r.method_used for r in records] == ["moving_average", "moving_average", "xgboost"]
    a = records[2].selection_analysis
    assert a["best_method"] == "moving_average"
    assert a["fallback_reason"] and "Moving Average" in a["fallback_reason"]
    assert records[0].selection_analysis.get("fallback_reason") is None
