"""
Exponential Smoothing (SES manual) — 1 fungsi (v3.0). Fₜ₊₁ = αDₜ + (1−α)Fₜ.
α di-tuning grid 0,1–0,9 saat backtest, pilih α dengan MAPE in-sample terendah
(implementasi manual sesuai rumus Bab III thesis, bukan statsmodels).

Kontrak: docs/ARCHITECTURE.md §6.4 dan engines/README.md.
"""
import numpy as np

from app.config import get_settings
from app.services.forecasting.engines._common import build_points, resid_std
from app.services.forecasting.evaluation import backtest_metrics, mape
from app.services.forecasting.metrics import train_test_split_series
from app.services.forecasting.preprocessing import to_period_series
from app.services.forecasting.types import EngineResult

_ALPHA_GRID = [round(a, 1) for a in np.arange(0.1, 1.0, 0.1)]


def _ses(values: np.ndarray, alpha: float) -> tuple[np.ndarray, float]:
    """One-step in-sample forecasts + level periode berikutnya."""
    fitted = np.zeros(len(values))
    fitted[0] = values[0]
    for t in range(1, len(values)):
        fitted[t] = alpha * values[t - 1] + (1 - alpha) * fitted[t - 1]
    next_level = alpha * values[-1] + (1 - alpha) * fitted[-1]
    return fitted, next_level


def _best_alpha(values: np.ndarray) -> float:
    """Pilih α dengan MAPE in-sample one-step terendah (skip titik pertama)."""
    best_alpha, best_err = _ALPHA_GRID[0], float("inf")
    for alpha in _ALPHA_GRID:
        fitted, _ = _ses(values, alpha)
        err = mape(values[1:], fitted[1:]) if len(values) > 1 else 0.0
        if err < best_err:
            best_alpha, best_err = alpha, err
    return best_alpha


def forecast_exponential_smoothing(df, horizon: int) -> EngineResult:
    settings = get_settings()
    series = to_period_series(df)
    train, test = train_test_split_series(series, horizon)

    train_values = train.to_numpy(dtype=float)
    alpha = _best_alpha(train_values)
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
        f"Exponential Smoothing (α={alpha}) memberi bobot lebih ke observasi terbaru; "
        f"proyeksi level {final_level:.2f}. MAPE backtest: {metrics['mape']:.2f}%."
    )
    return EngineResult(forecast=points, explanation=explanation, **metrics)
