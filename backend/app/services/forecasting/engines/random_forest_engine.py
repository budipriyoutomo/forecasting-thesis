"""
Random Forest — 1 fungsi (v3.0). RandomForestRegressor(n_estimators=100, max_depth=10),
fitur lag + bulan (+ variabel eksternal aktif); forecast rekursif multi-step (Bab III thesis).

Lag disesuaikan periodisitas bulanan data thesis (lag_1 + lag_12 musiman); lag yang
melebihi panjang histori dibuang otomatis (lihat engines/_ml.py).

Fase 11.2: feature importance (embedded) disimpan; grid search `_PARAM_GRID` dengan
TimeSeriesSplit bila `options.ml_grid_search` (Pengaturan Forecast).

Kontrak: docs/ARCHITECTURE.md §6.4 dan engines/README.md.
"""
from sklearn.ensemble import RandomForestRegressor

from app.config import get_settings
from app.services.forecasting.engines._common import build_points, resid_std
from app.services.forecasting.engines._ml import run_supervised
from app.services.forecasting.evaluation import backtest_metrics
from app.services.forecasting.preprocessing import to_period_series
from app.services.forecasting.types import EngineOptions, EngineResult

_LAGS = [1, 12]
_PARAM_GRID = {"n_estimators": [100, 200], "max_depth": [5, 10]}


def _model() -> RandomForestRegressor:
    return RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=1)


def forecast_random_forest(df, horizon: int, options: EngineOptions | None = None) -> EngineResult:
    settings = get_settings()
    series = to_period_series(df)
    run = run_supervised(_model, _PARAM_GRID, series, _LAGS, horizon, options)
    metrics = backtest_metrics(
        run.test.to_numpy(), run.test_pred, run.train.to_numpy(), compute_mase=settings.COMPUTE_MASE
    )

    std = resid_std(run.test.to_numpy(), run.test_pred, series)
    points = build_points(series, run.values, std)
    top = next(iter(run.feature_importance))
    explanation = (
        f"Random Forest ({run.hyperparameters['best_params'].get('n_estimators')} pohon, fitur lag "
        f"{run.lags} + bulan) menangkap pola non-linear dari histori; fitur terpenting {top}. "
        f"MAPE backtest: {metrics['mape']:.2f}%."
    )
    return EngineResult(
        forecast=points,
        explanation=explanation,
        feature_importance=run.feature_importance,
        hyperparameters=run.hyperparameters,
        **metrics,
    )
