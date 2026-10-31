"""
Fase 11.2 (REVISI_V2 §3.6) — opsi engine dari master data Pengaturan Forecast.

a. α ES = grid thesis {0,01; 0,05; 0,15; 0,2; 0,8; 0,95; 0,99}, dipilih by MAD.
c. Label interpretasi MAPE (Lewis): <10 sangat baik, 10–20 baik, 20–50 cukup, >50 buruk.
d. Feature importance RF/XGB disimpan.
e. Grid search (TimeSeriesSplit) RF/XGB, aktif via opsi.
f. Outlier IQR (winsorize) sebelum training ML, aktif via opsi.
"""
import math

import numpy as np
import pandas as pd
import pytest

from app.services.forecasting.engines.exponential_smoothing_engine import (
    _best_alpha,
    forecast_exponential_smoothing,
)
from app.services.forecasting.engines.random_forest_engine import forecast_random_forest
from app.services.forecasting.engines.xgboost_engine import forecast_xgboost
from app.services.forecasting.evaluation import mape_interpretation
from app.services.forecasting.preprocessing import cap_outliers_iqr
from app.services.forecasting.types import THESIS_ALPHA_GRID, EngineOptions


def _monthly_df(values):
    dates = pd.date_range("2024-01-01", periods=len(values), freq="MS")
    return pd.DataFrame({"date": dates, "quantity": values})


SERIES = [10 + i + (i % 3) * 2 for i in range(30)]  # 30 bulan: cukup sampel untuk grid search


# ── a. α ES ──


def test_grid_alpha_thesis():
    assert THESIS_ALPHA_GRID == (0.01, 0.05, 0.15, 0.2, 0.8, 0.95, 0.99)
    assert EngineOptions().es_alpha_grid == THESIS_ALPHA_GRID
    assert EngineOptions().es_alpha_metric == "mad"


def test_best_alpha_berdasarkan_mad():
    values = np.asarray(SERIES, dtype=float)
    alpha = _best_alpha(values, THESIS_ALPHA_GRID, "mad")

    def in_sample(a, metric):
        fitted = np.zeros(len(values))
        fitted[0] = values[0]
        for t in range(1, len(values)):
            fitted[t] = a * values[t - 1] + (1 - a) * fitted[t - 1]
        err = values[1:] - fitted[1:]
        return np.mean(np.abs(err)) if metric == "mad" else np.mean(np.abs(err / values[1:]))

    expected = min(THESIS_ALPHA_GRID, key=lambda a: in_sample(a, "mad"))
    assert alpha == expected


def test_es_alpha_dari_grid_opsi_dan_tercatat():
    res = forecast_exponential_smoothing(_monthly_df(SERIES), 3, options=EngineOptions(es_alpha_grid=(0.2,)))
    assert res.hyperparameters == {"alpha": 0.2, "alpha_metric": "mad"}
    assert "α=0.2" in res.explanation


def test_es_default_alpha_di_grid_thesis():
    res = forecast_exponential_smoothing(_monthly_df(SERIES), 3)
    assert res.hyperparameters["alpha"] in THESIS_ALPHA_GRID


# ── c. Label MAPE ──


@pytest.mark.parametrize(
    "value,label",
    [(5, "Sangat baik"), (10, "Baik"), (19.9, "Baik"), (20, "Cukup"), (50, "Buruk"), (80, "Buruk")],
)
def test_mape_interpretation(value, label):
    assert mape_interpretation(value) == label


@pytest.mark.parametrize("value", [None, math.inf, float("nan")])
def test_mape_interpretation_tak_terdefinisi(value):
    assert mape_interpretation(value) == "Tidak terdefinisi"


# ── d. Feature importance ──


@pytest.mark.parametrize("engine", [forecast_random_forest, forecast_xgboost])
def test_feature_importance_ml(engine):
    res = engine(_monthly_df(SERIES), 3)

    fi = res.feature_importance
    assert "lag_1" in fi and "month" in fi
    assert sum(fi.values()) == pytest.approx(1.0, abs=1e-6)
    assert all(v >= 0 for v in fi.values())
    assert list(fi.values()) == sorted(fi.values(), reverse=True)  # terpenting dulu


# ── e. Grid search ──


@pytest.mark.parametrize("engine", [forecast_random_forest, forecast_xgboost])
def test_hyperparameter_tetap_tanpa_grid_search(engine):
    res = engine(_monthly_df(SERIES), 3)
    assert res.hyperparameters["grid_search"] is False


@pytest.mark.parametrize("engine", [forecast_random_forest, forecast_xgboost])
def test_grid_search_mencatat_parameter_terbaik(engine):
    res = engine(_monthly_df(SERIES), 3, options=EngineOptions(ml_grid_search=True))

    hp = res.hyperparameters
    assert hp["grid_search"] is True
    assert hp["cv_splits"] >= 2
    assert "max_depth" in hp["best_params"]
    assert len(res.forecast) == 3


def test_grid_search_data_terlalu_pendek_fallback_parameter_tetap():
    res = forecast_random_forest(_monthly_df(SERIES[:6]), 2, options=EngineOptions(ml_grid_search=True))
    assert res.hyperparameters["grid_search"] is False  # sampel < 2 fold → tidak di-tuning


# ── f. Outlier IQR ──


def test_cap_outliers_iqr():
    s = pd.Series([10, 11, 12, 10, 11, 200, 12, 11], dtype=float)
    capped, n = cap_outliers_iqr(s)

    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    upper = q3 + 1.5 * (q3 - q1)
    assert n == 1
    assert capped.max() == pytest.approx(upper)
    assert capped.iloc[0] == 10  # titik normal tidak diubah


def test_winsorize_tercatat_di_hyperparameters():
    values = SERIES[:]
    values[5] = 500
    res = forecast_random_forest(_monthly_df(values), 3, options=EngineOptions(ml_winsorize=True))
    assert res.hyperparameters["outliers_capped"] == 1


# ── Variabel eksternal (Fase 11.2b) ──


def _exog(n_hist, horizon, cols):
    idx = pd.date_range("2024-01-01", periods=n_hist + horizon, freq="MS")
    return pd.DataFrame({c: np.arange(len(idx), dtype=float) % 3 for c in cols}, index=idx)


@pytest.mark.parametrize("engine", [forecast_random_forest, forecast_xgboost])
def test_exog_lengkap_dipakai_sebagai_fitur(engine):
    exog = _exog(len(SERIES), 3, ["suhu", "promo"])
    res = engine(_monthly_df(SERIES), 3, options=EngineOptions(exog=exog))

    assert res.hyperparameters["exog_used"] == ["suhu", "promo"]
    assert "suhu" in res.feature_importance and "promo" in res.feature_importance


def test_exog_tanpa_nilai_horizon_di_drop():
    exog = _exog(len(SERIES), 0, ["suhu"])  # tidak ada nilai untuk periode horizon
    res = forecast_random_forest(_monthly_df(SERIES), 3, options=EngineOptions(exog=exog))

    assert res.hyperparameters["exog_used"] == []
    assert res.hyperparameters["exog_dropped"] == ["suhu"]
    assert "suhu" not in res.feature_importance


def test_future_dates_bulanan_tetap_awal_bulan():
    from app.services.forecasting.preprocessing import future_dates

    delta = pd.Timedelta(days=31)  # median selisih data bulanan
    assert future_dates("2026-01-01", 3, delta) == ["2026-02-01", "2026-03-01", "2026-04-01"]
    assert future_dates("2026-01-31", 2, delta) == ["2026-02-28", "2026-03-31"]  # akhir bulan
    assert future_dates("2026-01-05", 2, pd.Timedelta(days=7)) == ["2026-01-12", "2026-01-19"]
