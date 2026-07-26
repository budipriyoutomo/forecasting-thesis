"""
ARIMA — 1 fungsi, cocok untuk kuadran `smooth` (tanpa musiman kuat) dan
`intermittent` (jika data cukup).

Order dipilih otomatis dari beberapa kandidat kecil berdasarkan AIC terendah —
pendekatan ringan tanpa dependency tambahan (mis. pmdarima) yang berat untuk
build. Kontrak: lihat docs/ARCHITECTURE.md §6.0/§6.6.
"""
import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA

from app.services.forecasting.metrics import mean_absolute_scaled_error, train_test_split_series
from app.services.forecasting.preprocessing import to_daily_series
from app.services.forecasting.types import EngineResult, ForecastPoint

CANDIDATE_ORDERS = [(1, 1, 1), (1, 1, 0), (0, 1, 1), (2, 1, 1)]


def _fit_best_order(series: pd.Series):
    best_model = None
    best_aic = float("inf")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for order in CANDIDATE_ORDERS:
            try:
                fitted = ARIMA(series, order=order).fit()
                if fitted.aic < best_aic:
                    best_aic, best_model = fitted.aic, fitted
            except Exception:
                continue
    if best_model is None:
        # fail-safe terakhir: order paling sederhana yang hampir selalu konvergen
        best_model = ARIMA(series, order=(0, 1, 0)).fit()
    return best_model


def forecast_arima(df: pd.DataFrame, horizon: int) -> EngineResult:
    series = to_daily_series(df)
    train, test = train_test_split_series(series, horizon)

    try:
        backtest_model = _fit_best_order(train)
        test_pred = backtest_model.forecast(len(test))
        mase = mean_absolute_scaled_error(test.to_numpy(), test_pred.to_numpy(), train.to_numpy())
    except Exception:
        mase = float("inf")

    final_model = _fit_best_order(series)
    forecast_res = final_model.get_forecast(horizon)
    forecast_values = forecast_res.predicted_mean
    conf_int = forecast_res.conf_int(alpha=0.05)

    last_date = series.index.max()
    forecast_points = []
    for i in range(horizon):
        value = float(forecast_values.iloc[i])
        lower = float(conf_int.iloc[i, 0])
        upper = float(conf_int.iloc[i, 1])
        forecast_points.append(
            ForecastPoint(
                date=str((last_date + pd.Timedelta(days=i + 1)).date()),
                value=value,
                lower=lower,
                upper=upper,
            )
        )

    explanation = (
        f"Metode ARIMA{final_model.model.order} dipilih karena data historis relatif stasioner "
        f"tanpa pola musiman kuat. Akurasi historis (MASE): {mase:.2f}."
    )

    return EngineResult(forecast=forecast_points, mase=mase, explanation=explanation)
