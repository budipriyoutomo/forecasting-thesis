"""
Exponential Smoothing (SES manual) — 1 fungsi (v3.0). Fₜ₊₁ = αDₜ + (1−α)Fₜ.
α dicoba satu per satu dari grid thesis {0,01; 0,05; 0,15; 0,2; 0,8; 0,95; 0,99} dan
dipilih dengan MAD in-sample terendah (Fase 11.2; grid & metrik bisa diubah di
Pengaturan Forecast). Implementasi manual sesuai rumus Bab III thesis, bukan statsmodels.

Kontrak: docs/ARCHITECTURE.md §6.4 dan engines/README.md.
"""
import numpy as np

from app.config import get_settings
from app.services.forecasting.engines._common import build_points, resid_std
from app.services.forecasting.evaluation import backtest_metrics, mad, mape
from app.services.forecasting.metrics import train_test_split_series
from app.services.forecasting.preprocessing import to_period_series
from app.services.forecasting.types import EngineOptions, EngineResult

_METRICS = {"mad": mad, "mape": mape}


def _ses(values: np.ndarray, alpha: float) -> tuple[np.ndarray, float]:
    """One-step in-sample forecasts + level periode berikutnya."""
    fitted = np.zeros(len(values))
    fitted[0] = values[0]
    for t in range(1, len(values)):
        fitted[t] = alpha * values[t - 1] + (1 - alpha) * fitted[t - 1]
    next_level = alpha * values[-1] + (1 - alpha) * fitted[-1]
    return fitted, next_level


def _best_alpha(values: np.ndarray, grid, metric: str = "mad") -> float:
    """Pilih α dengan galat in-sample one-step terendah (skip titik pertama). Seri → α
    pertama di grid."""
    err_fn = _METRICS.get(metric, mad)
    best_alpha, best_err = grid[0], float("inf")
    for alpha in grid:
        fitted, _ = _ses(values, alpha)
        err = err_fn(values[1:], fitted[1:]) if len(values) > 1 else 0.0
        if err < best_err:
            best_alpha, best_err = alpha, err
    return best_alpha


def forecast_exponential_smoothing(df, horizon: int, options: EngineOptions | None = None) -> EngineResult:
    settings = get_settings()
    options = options or EngineOptions()
    metric = options.es_alpha_metric if options.es_alpha_metric in _METRICS else "mad"
    series = to_period_series(df)
    train, test = train_test_split_series(series, horizon)

    train_values = train.to_numpy(dtype=float)
    alpha = _best_alpha(train_values, options.es_alpha_grid, metric)
    _, train_level = _ses(train_values, alpha)
    test_pred = np.full(len(test), train_level)
    metrics = backtest_metrics(
        test.to_numpy(), test_pred, train_values, compute_mase=settings.COMPUTE_MASE
    )

    _, final_level = _ses(series.to_numpy(dtype=float), alpha)
    values = np.full(horizon, final_level)

    std = resid_std(test.to_numpy(), test_pred, series)
    points = build_points(series, values, std)
    explanation = (
        f"Exponential Smoothing (α={alpha}, dipilih dari {len(options.es_alpha_grid)} kandidat α "
        f"dengan {metric.upper()} terendah) memberi bobot lebih ke observasi terbaru; "
        f"proyeksi level {final_level:.2f}. MAPE backtest: {metrics['mape']:.2f}%."
    )
    return EngineResult(
        forecast=points,
        explanation=explanation,
        hyperparameters={"alpha": alpha, "alpha_metric": metric},
        **metrics,
    )
