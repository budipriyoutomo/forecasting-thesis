"""
Test orkestrasi forecast_service v3.0 — Comparative Selection vs manual
(AGENTS.md §5, docs/ARCHITECTURE.md §6.1). Tidak ada lagi klasifikasi kuadran.
"""
import pytest

from app.services.forecasting.forecast_service import run_forecast_for_product
from app.utils.exceptions import UnsupportedForecastMethodError

_ACTIVE = {"moving_average", "exponential_smoothing", "random_forest", "xgboost"}


def test_auto_mode_membandingkan_semua_metode(smooth_df):
    record = run_forecast_for_product(smooth_df, horizon=7, requested_method=None)

    assert record.status == "COMPLETED"
    assert record.selection_mode == "auto"
    assert record.method_used in _ACTIVE  # lstm auto-excluded (TF absen)
    assert len(record.forecast) == 7
    # candidates_evaluated menyimpan SEMUA kandidat yang berhasil (transparansi)
    methods = {c["method"] for c in record.candidates_evaluated}
    assert methods == _ACTIVE
    # pemenang = MAPE terendah (default FORECAST_RANKING_METRIC)
    best = min(record.candidates_evaluated, key=lambda c: c["mape"])
    assert record.method_used == best["method"]


def test_auto_mode_metrik_pemenang_terisi(erratic_df):
    record = run_forecast_for_product(erratic_df, horizon=5)
    assert record.status == "COMPLETED"
    for m in (record.mad, record.mfe, record.mse, record.mape):
        assert m is not None
    assert record.mase is not None  # COMPUTE_MASE default true


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


def test_auto_mode_explanation_menyebut_dasar_perbandingan(smooth_df):
    """Mode otomatis harus menjelaskan MENGAPA pemenang menang, bukan cuma
    menyalin penjelasan engine — `candidates_evaluated` disimpan justru untuk
    transparansi ini (docs/ARCHITECTURE.md §4 kolom candidates_evaluated)."""
    record = run_forecast_for_product(smooth_df, horizon=7, requested_method=None)

    assert record.explanation
    exp = record.explanation.lower()
    assert record.method_used in exp  # pemenang disebut
    assert "mape" in exp  # metrik ranking yang dipakai
    assert str(len(record.candidates_evaluated)) in exp  # berapa metode dibandingkan
    # runner-up disebut agar planner tahu selisihnya tipis atau jauh
    runner_up = sorted(record.candidates_evaluated, key=lambda c: c["mape"])[1]
    assert runner_up["method"] in exp


def test_manual_mode_explanation_tidak_mengaku_membandingkan(smooth_df):
    """Mode manual tidak membandingkan apa pun — jangan tempel narasi perbandingan."""
    record = run_forecast_for_product(smooth_df, horizon=7, requested_method="moving_average")

    assert record.explanation
    assert "dibandingkan" not in record.explanation.lower()
