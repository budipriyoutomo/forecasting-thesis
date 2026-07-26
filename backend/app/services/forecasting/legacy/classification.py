"""
Klasifikasi pola demand — ADI/CV² → kuadran Syntetos-Boylan.

Lihat AGENTS.md §5 dan docs/ARCHITECTURE.md §6.2. Dipakai HANYA di mode
otomatis (forecast_service.run_forecast_for_material tanpa `requested_method`)
untuk memfilter engine kandidat — tapi tetap dihitung di mode manual juga,
sekadar untuk ditampilkan sebagai konteks ke user (lihat §6.1).

Simplifikasi MVP: demand di-resample ke frekuensi harian (hari tanpa transaksi
dianggap quantity=0) untuk menghitung ADI/CV². Ini cukup untuk MVP tapi belum
frequency-aware (mis. data yang aslinya bulanan akan punya ADI besar secara
struktural) — jadikan TODO Fase lanjutan kalau granularitas data ternyata
bervariasi antar material.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller

from app.services.forecasting.preprocessing import to_daily_series

SMOOTH = "smooth"
ERRATIC = "erratic"
INTERMITTENT = "intermittent"
LUMPY = "lumpy"

ADI_THRESHOLD = 1.32
CV2_THRESHOLD = 0.49


@dataclass
class DemandProfile:
    n_points: int
    adi: float
    cv2: float
    demand_class: str
    has_seasonality: bool
    is_stationary: bool
    missing_ratio: float
    has_outliers: bool


def compute_adi(series: pd.Series) -> float:
    n_periods = len(series)
    n_nonzero = int((series != 0).sum())
    if n_nonzero == 0:
        return float("inf")
    return n_periods / n_nonzero


def compute_cv2(series: pd.Series) -> float:
    nonzero = series[series != 0]
    if len(nonzero) < 2 or nonzero.mean() == 0:
        return 0.0
    return float((nonzero.std(ddof=0) / nonzero.mean()) ** 2)


def syntetos_boylan_quadrant(adi: float, cv2: float) -> str:
    if adi < ADI_THRESHOLD and cv2 < CV2_THRESHOLD:
        return SMOOTH
    if adi < ADI_THRESHOLD and cv2 >= CV2_THRESHOLD:
        return ERRATIC
    if adi >= ADI_THRESHOLD and cv2 < CV2_THRESHOLD:
        return INTERMITTENT
    return LUMPY


def _detect_outliers_iqr(series: pd.Series) -> bool:
    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return False
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return bool(((series < lower) | (series > upper)).any())


def _detect_seasonality(series: pd.Series, lag: int = 7) -> bool:
    """Deteksi musiman sederhana lewat autocorrelation di lag mingguan (naif, cukup untuk MVP)."""
    if len(series) <= lag * 2:
        return False
    shifted = series.shift(lag)
    valid = pd.DataFrame({"a": series, "b": shifted}).dropna()
    if len(valid) < 2 or valid["a"].std() == 0 or valid["b"].std() == 0:
        return False
    corr = valid["a"].corr(valid["b"])
    return bool(corr is not None and not np.isnan(corr) and corr > 0.3)


def _is_stationary(series: pd.Series) -> bool:
    """Augmented Dickey-Fuller test — p-value < 0.05 dianggap stasioner."""
    if series.nunique() <= 1 or len(series) < 8:
        return True  # data konstan/terlalu pendek dianggap stasioner secara default
    try:
        p_value = adfuller(series, autolag="AIC")[1]
        return bool(p_value < 0.05)
    except Exception:
        return True  # fail-safe: jangan sampai klasifikasi gagal total gara-gara ADF error


def classify(df: pd.DataFrame) -> DemandProfile:
    series = to_daily_series(df)
    adi = compute_adi(series)
    cv2 = compute_cv2(series)

    return DemandProfile(
        n_points=len(df),
        adi=adi,
        cv2=cv2,
        demand_class=syntetos_boylan_quadrant(adi, cv2),
        has_seasonality=_detect_seasonality(series),
        is_stationary=_is_stationary(series),
        missing_ratio=float(df["quantity"].isna().mean()),
        has_outliers=_detect_outliers_iqr(series[series != 0]) if (series != 0).any() else False,
    )
