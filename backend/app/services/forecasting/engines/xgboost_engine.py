"""
XGBoost — 1 fungsi (v3.0). XGBRegressor dengan fitur lag + kalender, forecast
rekursif multi-step (Bab III thesis).

Catatan: thesis menyebut tuning via GridSearchCV. Pada data bulanan pendek (< ~40
titik), grid search cross-validation rapuh/lambat, jadi dipakai hyperparameter tetap
yang wajar & deterministik (random_state=42). Bila volume data besar, tuning bisa
diaktifkan tanpa mengubah kontrak fungsi.

Kontrak: docs/ARCHITECTURE.md §6.4 dan engines/README.md.
"""
from xgboost import XGBRegressor

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

_LAGS = [1, 2, 12]


def _model() -> XGBRegressor:
    return XGBRegressor(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.1,
        subsample=0.9,
        random_state=42,
        n_jobs=1,
        verbosity=0,
    )


def forecast_xgboost(df, horizon: int) -> EngineResult:
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
        f"XGBoost (gradient boosting, fitur lag {used} + bulan) memodelkan interaksi "
        f"non-linear antar periode. MAPE backtest: {metrics['mape']:.2f}%."
    )
    return EngineResult(forecast=points, explanation=explanation, **metrics)
