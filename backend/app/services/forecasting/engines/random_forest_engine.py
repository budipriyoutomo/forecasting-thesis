"""
Random Forest — 1 fungsi (v3.0). RandomForestRegressor(n_estimators=100, max_depth=10),
fitur lag + bulan; forecast rekursif multi-step (Bab III thesis).

Lag disesuaikan periodisitas bulanan data thesis (lag_1 + lag_12 musiman); lag yang
melebihi panjang histori dibuang otomatis (lihat engines/_ml.py).

Kontrak: docs/ARCHITECTURE.md §6.4 dan engines/README.md.
"""
from sklearn.ensemble import RandomForestRegressor

from app.config import get_settings
from app.services.forecasting.engines._common import build_points, resid_std
from app.services.forecasting.engines._ml import (
    build_supervised,
    fit_and_backtest,
    recursive_forecast,
)
from app.services.forecasting.evaluation import backtest_metrics
from app.services.forecasting.metrics import train_test_split_series
from app.services.forecasting.preprocessing import to_period_series
from app.services.forecasting.types import EngineResult

_LAGS = [1, 12]


def _model() -> RandomForestRegressor:
    return RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=1)


def forecast_random_forest(df, horizon: int) -> EngineResult:
    settings = get_settings()
    series = to_period_series(df)
    _, test = train_test_split_series(series, horizon)
    train = series.iloc[: len(series) - len(test)]

    test_pred, _ = fit_and_backtest(_model, series, _LAGS, len(test))
    metrics = backtest_metrics(
        test.to_numpy(), test_pred, train.to_numpy(), compute_mase=settings.COMPUTE_MASE
    )

    X, y, used = build_supervised(series, _LAGS)
    model = _model()
    model.fit(X, y)
    values = recursive_forecast(model, series, used, horizon)

    std = resid_std(test.to_numpy(), test_pred, series)
    points = build_points(series, values, std)
    explanation = (
        f"Random Forest (100 pohon, fitur lag {used} + bulan) menangkap pola non-linear "
        f"dari histori. MAPE backtest: {metrics['mape']:.2f}%."
    )
    return EngineResult(forecast=points, explanation=explanation, **metrics)
