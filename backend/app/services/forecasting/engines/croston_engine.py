"""
Croston's Method (dengan koreksi SBA — Syntetos-Boylan Approximation) — 1 fungsi,
WAJIB untuk kuadran `intermittent` dan `lumpy` (lihat docs/RECONCILIATION.md:
tanpa ini, kuadran tsb tidak punya kandidat engine sama sekali).

Implementasi manual (tanpa dependency tambahan) — Croston memisahkan demand
jadi dua deret: ukuran demand saat terjadi (non-zero) dan interval antar
kejadian demand, lalu men-smooth keduanya secara terpisah dengan simple
exponential smoothing. Forecast = ukuran_demand_smoothed / interval_smoothed
(rate per periode), dikoreksi faktor SBA `(1 - alpha/2)` untuk mengurangi bias
Croston asli yang cenderung over-forecast.
"""
import numpy as np
import pandas as pd

from app.services.forecasting.metrics import mean_absolute_scaled_error, train_test_split_series
from app.services.forecasting.preprocessing import to_daily_series
from app.services.forecasting.types import EngineResult, ForecastPoint

DEFAULT_ALPHA = 0.1


def _croston_smoothed_rate(values: np.ndarray, alpha: float = DEFAULT_ALPHA) -> float:
    """Fit Croston/SBA di atas satu deret nilai, kembalikan estimasi rate per periode."""
    z_hat: float | None = None
    p_hat: float | None = None
    interval = 0

    for v in values:
        interval += 1
        if v > 0:
            if z_hat is None:
                z_hat, p_hat = float(v), float(interval)
            else:
                z_hat = alpha * v + (1 - alpha) * z_hat
                p_hat = alpha * interval + (1 - alpha) * p_hat
            interval = 0

    if z_hat is None or not p_hat:
        return 0.0  # tidak pernah ada demand non-zero sama sekali

    sba_correction = 1 - (alpha / 2)
    return sba_correction * (z_hat / p_hat)


def forecast_croston(df: pd.DataFrame, horizon: int) -> EngineResult:
    series = to_daily_series(df)
    train, test = train_test_split_series(series, horizon)

    backtest_rate = _croston_smoothed_rate(train.to_numpy())
    test_pred = np.full(len(test), backtest_rate)
    mase = mean_absolute_scaled_error(test.to_numpy(), test_pred, train.to_numpy())

    final_rate = _croston_smoothed_rate(series.to_numpy())

    nonzero = series[series != 0]
    demand_std = float(nonzero.std()) if len(nonzero) > 1 else max(final_rate * 0.5, 1.0)

    last_date = series.index.max()
    forecast_points = [
        ForecastPoint(
            date=str((last_date + pd.Timedelta(days=i + 1)).date()),
            value=float(final_rate),
            lower=float(max(0.0, final_rate - demand_std)),
            upper=float(final_rate + demand_std),
        )
        for i in range(horizon)
    ]

    explanation = (
        "Metode Croston/SBA dipilih karena pola konsumsi bersifat intermittent/lumpy "
        "(jarang terjadi, tapi jumlahnya bervariasi saat terjadi) — metode standar industri "
        f"untuk demand seperti ini. Estimasi rata-rata kebutuhan: {final_rate:.2f} unit/hari. "
        f"Akurasi historis (MASE): {mase:.2f}."
    )

    return EngineResult(forecast=forecast_points, mase=mase, explanation=explanation)
