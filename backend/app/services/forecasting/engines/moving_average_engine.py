"""
Moving Average — 1 fungsi (v3.0). Fₜ₊₁ = rata-rata `n` periode terakhir;
n dikonfigurasi lewat MOVING_AVERAGE_WINDOW (default 3). Baseline konvensional
pembanding metode ML (Bab III thesis).

Kontrak: docs/ARCHITECTURE.md §6.4 dan engines/README.md.
"""
import numpy as np

from app.config import get_settings
from app.services.forecasting.engines._common import build_points, resid_std
from app.services.forecasting.evaluation import backtest_metrics
from app.services.forecasting.metrics import train_test_split_series
from app.services.forecasting.preprocessing import to_period_series
from app.services.forecasting.types import EngineResult


def forecast_moving_average(df, horizon: int) -> EngineResult:
    settings = get_settings()
    window = max(1, int(settings.MOVING_AVERAGE_WINDOW))

    series = to_period_series(df)
    train, test = train_test_split_series(series, horizon)

    # Backtest: forecast flat = rata-rata `window` terakhir data train, dibandingkan holdout.
    train_ma = float(np.mean(train.to_numpy()[-window:]))
    test_pred = np.full(len(test), train_ma)
    metrics = backtest_metrics(
        test.to_numpy(), test_pred, train.to_numpy(), compute_mase=settings.COMPUTE_MASE
    )

    # Forecast final: rata-rata `window` terakhir SELURUH data, flat sepanjang horizon.
    final_ma = float(np.mean(series.to_numpy()[-window:]))
    values = np.full(horizon, final_ma)

    std = resid_std(test.to_numpy(), test_pred, series)
    points = build_points(series, values, std)
    explanation = (
        f"Moving Average (window {window}) memproyeksikan rata-rata {window} periode "
        f"terakhir ({final_ma:.2f}) secara flat. MAPE backtest: {metrics['mape']:.2f}% — "
        f"makin kecil makin akurat."
    )
    return EngineResult(forecast=points, explanation=explanation, **metrics)
