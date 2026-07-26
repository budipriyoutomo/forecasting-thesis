"""
Utilitas supervised-learning bersama untuk engine ML (Random Forest, XGBoost) —
BUKAN metode forecasting (diawali `_`, tak didaftarkan), jadi tidak melanggar
1-fungsi-1-metode (AGENTS.md §5).

Membentuk fitur lag + kalender dari time series & melakukan forecast rekursif
multi-step. Set lag disesuaikan panjang data (data thesis bulanan; lag yang
melebihi panjang histori otomatis dibuang).
"""
import numpy as np
import pandas as pd

from app.services.forecasting.preprocessing import infer_period_delta


def usable_lags(n: int, lags: list[int]) -> list[int]:
    fit = [lag for lag in lags if lag < n]
    return fit or ([1] if n > 1 else [])


def build_supervised(series: pd.Series, lags: list[int]) -> tuple[np.ndarray, np.ndarray, list[int]]:
    """Bangun matriks fitur [lag..., bulan] → target. Baris < max(lag) dibuang."""
    values = series.to_numpy(dtype=float)
    months = series.index.month
    n = len(values)
    lags = usable_lags(n, lags)
    start = max(lags) if lags else 1
    rows, targets = [], []
    for i in range(start, n):
        rows.append([values[i - lag] for lag in lags] + [int(months[i])])
        targets.append(values[i])
    return np.asarray(rows, dtype=float), np.asarray(targets, dtype=float), lags


def recursive_forecast(model, series: pd.Series, lags: list[int], horizon: int) -> np.ndarray:
    """Prediksi horizon ke depan secara rekursif (prediksi jadi input lag berikutnya)."""
    values = list(series.to_numpy(dtype=float))
    delta = infer_period_delta(series.index)
    last = pd.Timestamp(series.index.max())
    preds = []
    for h in range(horizon):
        step_month = (last + delta * (h + 1)).month
        row = [values[-lag] for lag in lags] + [int(step_month)]
        pred = float(model.predict(np.asarray([row], dtype=float))[0])
        preds.append(pred)
        values.append(pred)
    return np.asarray(preds, dtype=float)


def fit_and_backtest(fit_fn, series: pd.Series, lags: list[int], test_len: int):
    """
    Latih di train (tanpa `test_len` titik terakhir), prediksi rekursif holdout.
    Return (test_pred, used_lags). Raise bila data tak cukup membentuk 1 sampel.
    """
    train = series.iloc[: len(series) - test_len]
    X, y, used = build_supervised(train, lags)
    if len(X) == 0:
        raise ValueError("Data tidak cukup untuk membentuk fitur supervised.")
    model = fit_fn()
    model.fit(X, y)
    return recursive_forecast(model, train, used, test_len), used
