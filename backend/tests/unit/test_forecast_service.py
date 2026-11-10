"""
Test orkestrasi forecast_service — mode otomatis (semua metode, tanpa pemenang, Fase 11.15) vs manual
(AGENTS.md §5, docs/ARCHITECTURE.md §6.1). Tidak ada lagi klasifikasi kuadran.
"""
import pytest

from app.services.forecasting.forecast_service import run_forecast_for_product
from app.utils.exceptions import UnsupportedForecastMethodError

_ACTIVE = {"moving_average", "exponential_smoothing", "random_forest", "xgboost"}


def test_auto_mode_menjalankan_semua_metode_tanpa_pemenang(smooth_df):
    """Fase 11.15: mode otomatis TIDAK memilih metode — planner yang memilih per produk."""
    record = run_forecast_for_product(smooth_df, horizon=7, requested_method=None)

    assert record.status == "COMPLETED"
    assert record.selection_mode == "auto"
    assert record.method_used is None
    assert record.forecast is None
    assert record.mad is None and record.mape is None
    # candidates_evaluated menyimpan SEMUA kandidat yang berhasil (lstm auto-excluded, TF absen)
    assert {c["method"] for c in record.candidates_evaluated} == _ACTIVE


def test_auto_mode_kandidat_membawa_deret_forecast_dan_penjelasan(smooth_df):
    """Deret forecast tiap kandidat disimpan supaya planner bisa memilih metode setelah run."""
    record = run_forecast_for_product(smooth_df, horizon=7)

    for c in record.candidates_evaluated:
        assert len(c["forecast"]) == 7
        assert {"date", "value", "lower", "upper"} <= set(c["forecast"][0])
        assert "interpretasi mape" in c["explanation"].lower()
        for key in ("mad", "mfe", "mse", "mape"):
            assert c[key] is not None


def test_auto_mode_tanpa_peringkat(smooth_df):
    record = run_forecast_for_product(smooth_df, horizon=7)

    for c in record.candidates_evaluated:
        assert not any(k.startswith("rank_") for k in c)


def test_auto_mode_explanation_meminta_planner_memilih(smooth_df):
    record = run_forecast_for_product(smooth_df, horizon=7)

    exp = record.explanation.lower()
    assert "pilih" in exp
    assert "menang" not in exp and "terbaik" not in exp


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
