"""
Utilitas bersama fungsi engine v3.0 — BUKAN metode forecasting (diawali `_`,
tidak didaftarkan ke registry), jadi tidak melanggar 1-fungsi-1-metode (AGENTS.md §5).

Membangun titik forecast + confidence interval dan menghitung sebaran residual,
supaya tiap engine tidak menduplikasi kode boilerplate yang sama.
"""
import numpy as np
import pandas as pd

from app.services.forecasting.preprocessing import future_dates, infer_period_delta
from app.services.forecasting.types import ForecastPoint


def resid_std(test: np.ndarray, test_pred: np.ndarray, series: pd.Series) -> float:
    """Sebaran residual holdout untuk lebar CI; fallback std series, minimal 1.0."""
    test, test_pred = np.asarray(test, dtype=float), np.asarray(test_pred, dtype=float)
    if len(test) and len(test) == len(test_pred):
        std = float(np.std(test - test_pred))
        if std > 0:
            return std
    fallback = float(series.std()) if len(series) > 1 else 0.0
    return fallback or 1.0


def build_points(series: pd.Series, values, std: float) -> list[ForecastPoint]:
    """Rangkai ForecastPoint dgn CI ±1.96σ, tanggal melangkah sesuai periode series."""
    values = np.asarray(values, dtype=float)
    delta = infer_period_delta(series.index)
    dates = future_dates(series.index.max(), len(values), delta)
    band = 1.96 * std
    return [
        ForecastPoint(date=d, value=float(v), lower=float(v - band), upper=float(v + band))
        for d, v in zip(dates, values)
    ]
