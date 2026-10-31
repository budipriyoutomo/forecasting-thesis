"""
XGBoost — 1 fungsi (v3.0). XGBRegressor dengan fitur lag + kalender (+ variabel
eksternal aktif), forecast rekursif multi-step (Bab III thesis).

Fase 11.2: hyperparameter tuning `GridSearchCV` + `TimeSeriesSplit` sesuai thesis,
aktif via `options.ml_grid_search` (Pengaturan Forecast). Nonaktif / sampel train
< MIN_TUNING_SAMPLES → hyperparameter tetap yang wajar & deterministik
(random_state=42). Batasan: data bulanan pendek membuat fold CV kecil — dicatat di
thesis. Feature importance (embedded) disimpan.

Kontrak: docs/ARCHITECTURE.md §6.4 dan engines/README.md.
"""
from xgboost import XGBRegressor

from app.config import get_settings
from app.services.forecasting.engines._common import build_points, resid_std
from app.services.forecasting.engines._ml import run_supervised
from app.services.forecasting.evaluation import backtest_metrics
from app.services.forecasting.preprocessing import to_period_series
from app.services.forecasting.types import EngineOptions, EngineResult

_LAGS = [1, 2, 12]
_PARAM_GRID = {"max_depth": [3, 4], "learning_rate": [0.05, 0.1]}


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


def forecast_xgboost(df, horizon: int, options: EngineOptions | None = None) -> EngineResult:
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
        f"XGBoost (gradient boosting, fitur lag {run.lags} + bulan) memodelkan interaksi "
        f"non-linear antar periode; fitur terpenting {top}. MAPE backtest: {metrics['mape']:.2f}%."
    )
    return EngineResult(
        forecast=points,
        explanation=explanation,
        feature_importance=run.feature_importance,
        hyperparameters=run.hyperparameters,
        **metrics,
    )
