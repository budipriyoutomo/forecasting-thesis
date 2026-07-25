"""
ETS (Exponential Smoothing) — 1 fungsi, cocok untuk kuadran `smooth`:
demand dengan tren sederhana, jarang nol, variabilitas rendah.

Kontrak: lihat docs/ARCHITECTURE.md §6.0/§6.6 dan engines/README.md.
"""
import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from app.services.forecasting.metrics import mean_absolute_scaled_error, train_test_split_series
from app.services.forecasting.preprocessing import to_daily_series
from app.services.forecasting.types import EngineResult, ForecastPoint

MIN_POINTS_FOR_TREND = 10


def _fit_holt(series: pd.Series):
    """Coba fit dengan tren dulu, degrade ke simple exponential smoothing kalau gagal/data sedikit."""
    if len(series) >= MIN_POINTS_FOR_TREND:
        try:
            return ExponentialSmoothing(
                series, trend="add", seasonal=None, initialization_method="estimated"
            ).fit()
        except Exception:
            pass
    return ExponentialSmoothing(series, trend=None, seasonal=None, initialization_method="estimated").fit()


def forecast_ets(df: pd.DataFrame, horizon: int) -> EngineResult:
    series = to_daily_series(df)
    train, test = train_test_split_series(series, horizon)

    try:
        backtest_model = _fit_holt(train)
        test_pred = backtest_model.forecast(len(test))
        mase = mean_absolute_scaled_error(test.to_numpy(), test_pred.to_numpy(), train.to_numpy())
    except Exception:
        mase = float("inf")

    final_model = _fit_holt(series)
    forecast_values = final_model.forecast(horizon)
    resid_std = float(np.nan_to_num(final_model.resid.std(), nan=series.std() or 1.0)) or 1.0

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
        f"Metode ETS (Exponential Smoothing) dipilih karena pola konsumsi relatif stabil "
        f"dengan tren sederhana (kuadran 'smooth'). Akurasi historis (MASE): {mase:.2f} "
        f"— semakin mendekati 0, semakin akurat dibanding tebakan naif."
    )

    return EngineResult(forecast=forecast_points, mase=mase, explanation=explanation)
