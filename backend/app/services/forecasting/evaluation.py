"""
Metrik evaluasi forecast v3.0 — MAD, MFE, MSE, MAPE (Bab III thesis).

Bukan "metode forecasting" — utilitas bersama dipakai semua fungsi engine untuk
menghitung akurasi holdout backtest, jadi tidak melanggar aturan 1-fungsi-1-metode
(AGENTS.md §5). MASE dipertahankan sebagai metrik tambahan opsional (COMPUTE_MASE)
lewat metrics.py legacy — bukan dipakai ranking default.
"""
import numpy as np

from app.services.forecasting.metrics import mean_absolute_scaled_error


def _pair(actual, forecast) -> tuple[np.ndarray, np.ndarray]:
    return np.asarray(actual, dtype=float), np.asarray(forecast, dtype=float)


def mad(actual, forecast) -> float:
    """Mean Absolute Deviation."""
    a, f = _pair(actual, forecast)
    return float(np.mean(np.abs(a - f)))


def mfe(actual, forecast) -> float:
    """Mean Forecast Error (bias): positif = under-forecast, negatif = over-forecast."""
    a, f = _pair(actual, forecast)
    return float(np.mean(a - f))


def mse(actual, forecast) -> float:
    """Mean Squared Error."""
    a, f = _pair(actual, forecast)
    return float(np.mean((a - f) ** 2))


def mape(actual, forecast) -> float:
    """
    Mean Absolute Percentage Error (%). Periode `actual == 0` dikecualikan
    (tetap bisa terjadi meski objek utama produk jadi). Bila SELURUH actual nol,
    MAPE tidak terdefinisi → kembalikan inf (metode dianggap terburuk saat ranking).
    """
    a, f = _pair(actual, forecast)
    mask = a != 0
    if not mask.any():
        return float("inf")
    return float(np.mean(np.abs((a[mask] - f[mask]) / a[mask])) * 100)


def backtest_metrics(actual, forecast, train_series, compute_mase: bool = True) -> dict:
    """Hitung seluruh metrik holdout sekaligus. `mase` None bila compute_mase False."""
    a, f = _pair(actual, forecast)
    metrics = {
        "mad": mad(a, f),
        "mfe": mfe(a, f),
        "mse": mse(a, f),
        "mape": mape(a, f),
        "mase": None,
    }
    if compute_mase:
        metrics["mase"] = mean_absolute_scaled_error(a, f, np.asarray(train_series, dtype=float))
    return metrics
