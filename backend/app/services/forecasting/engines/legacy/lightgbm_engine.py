"""
LightGBM — 1 fungsi, cocok untuk kuadran `erratic` (variabilitas tinggi,
data cukup besar, pola tidak mudah ditangkap model klasik).

Pendekatan: lag features + regresi, forecast multi-step secara rekursif
(prediksi 1 langkah dipakai lagi sebagai input untuk langkah berikutnya).
Kontrak: lihat docs/ARCHITECTURE.md §6.0/§6.6.
"""
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from app.services.forecasting.metrics import mean_absolute_scaled_error, train_test_split_series
from app.services.forecasting.preprocessing import to_daily_series
from app.services.forecasting.types import EngineResult, ForecastPoint

if TYPE_CHECKING:  # pragma: no cover
    from lightgbm import LGBMRegressor


def _n_lags_for(n_points: int) -> int:
    return max(2, min(7, n_points // 3))


def _make_lag_features(values: np.ndarray, n_lags: int) -> tuple[np.ndarray, np.ndarray]:
    X, y = [], []
    for i in range(n_lags, len(values)):
        X.append(values[i - n_lags : i])
        y.append(values[i])
    return np.array(X), np.array(y)


def _fit_lgbm(X: np.ndarray, y: np.ndarray) -> "LGBMRegressor":
    # Import di dalam fungsi: lightgbm butuh library native (libomp di macOS).
    # Kalau native lib-nya tidak ada, yang gagal hanya engine ini saat dipanggil —
    # bukan seluruh proses import registry/app (AGENTS.md §5, aturan failure engine).
    from lightgbm import LGBMRegressor

    model = LGBMRegressor(n_estimators=80, max_depth=3, min_child_samples=1, verbose=-1)
    model.fit(X, y)
    return model


def _recursive_forecast(model: "LGBMRegressor", history: list[float], n_lags: int, steps: int) -> list[float]:
    history = list(history)
    preds = []
    for _ in range(steps):
        x = np.array(history[-n_lags:]).reshape(1, -1)
        pred = float(model.predict(x)[0])
        preds.append(pred)
        history.append(pred)
    return preds


def forecast_lightgbm(df: pd.DataFrame, horizon: int) -> EngineResult:
    series = to_daily_series(df)
    values = series.to_numpy(dtype=float)
    n_lags = _n_lags_for(len(values))

    train, test = train_test_split_series(series, horizon)
    train_vals = train.to_numpy(dtype=float)
    test_vals = test.to_numpy(dtype=float)

    try:
        X_train, y_train = _make_lag_features(train_vals, n_lags)
        backtest_model = _fit_lgbm(X_train, y_train)
        test_pred = _recursive_forecast(backtest_model, train_vals.tolist(), n_lags, len(test_vals))
        mase = mean_absolute_scaled_error(test_vals, test_pred, train_vals)
    except Exception:
        mase = float("inf")

    X_full, y_full = _make_lag_features(values, n_lags)
    final_model = _fit_lgbm(X_full, y_full)
    forecast_values = _recursive_forecast(final_model, values.tolist(), n_lags, horizon)

    residuals = y_full - final_model.predict(X_full)
    resid_std = float(np.std(residuals)) if len(residuals) > 1 else max(float(np.std(values)), 1.0)

    last_date = series.index.max()
    forecast_points = [
        ForecastPoint(
            date=str((last_date + pd.Timedelta(days=i + 1)).date()),
            value=float(value),
            lower=float(value - 1.96 * resid_std),
            upper=float(value + 1.96 * resid_std),
        )
        for i, value in enumerate(forecast_values)
    ]

    explanation = (
        "Metode LightGBM dipilih karena pola konsumsi cukup bervariasi (kuadran 'erratic') "
        f"dan data historis cukup banyak untuk model berbasis machine learning. "
        f"Akurasi historis (MASE): {mase:.2f}."
    )

    return EngineResult(forecast=forecast_points, mase=mase, explanation=explanation)
