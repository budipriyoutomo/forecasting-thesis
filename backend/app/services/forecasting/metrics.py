"""
Metrik akurasi bersama (MASE) — utilitas, bukan "metode forecasting" itu
sendiri, jadi tidak melanggar aturan 1-fungsi-1-metode.
"""
import numpy as np


def mean_absolute_scaled_error(actual: np.ndarray, predicted: np.ndarray, train_series: np.ndarray) -> float:
    """
    MASE = MAE(forecast) / MAE(naive one-step forecast di data training).
    Dipilih sebagai metrik utama (bukan MAPE) karena tetap valid meski ada
    periode dengan konsumsi nol — umum terjadi pada raw material
    (lihat docs/RECONCILIATION.md).
    """
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    train_series = np.asarray(train_series, dtype=float)

    mae_forecast = np.mean(np.abs(actual - predicted))

    if len(train_series) < 2:
        naive_denom = 1e-9
    else:
        naive_denom = np.mean(np.abs(np.diff(train_series)))
        if naive_denom == 0 or np.isnan(naive_denom):
            naive_denom = 1e-9  # degradasi aman, bukan divide-by-zero crash

    return float(mae_forecast / naive_denom)


def train_test_split_series(series, horizon: int, min_train: int = 6):
    """
    Split holdout untuk backtest: ambil `test_size` titik terakhir sebagai
    data uji, sisanya untuk training. `test_size` dibatasi supaya training
    tidak jadi lebih pendek dari `min_train`.
    """
    test_size = min(horizon, max(1, len(series) // 5))
    test_size = min(test_size, max(1, len(series) - min_train))
    train = series.iloc[: len(series) - test_size]
    test = series.iloc[len(series) - test_size :]
    return train, test
