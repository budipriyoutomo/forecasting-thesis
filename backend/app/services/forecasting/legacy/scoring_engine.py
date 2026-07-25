"""
Weighted scoring — HANYA dipakai mode OTOMATIS (docs/ARCHITECTURE.md §6.4).
Mode manual skip modul ini sepenuhnya (lihat forecast_service.py).
"""
import math

from app.config import get_settings
from app.services.forecasting.legacy.classification import DemandProfile
from app.services.forecasting.preprocessing import to_daily_series
from app.services.forecasting.types import EngineResult

import pandas as pd

# Preferensi relatif antar-kandidat dalam kuadran yang sama (0-1). Dipakai
# sebagai salah satu dari 3 komponen skor — bukan penentu tunggal.
QUADRANT_FIT_SCORE: dict[str, dict[str, float]] = {
    "smooth": {"ets": 1.0, "arima": 0.8},
    "erratic": {"lgbm": 1.0, "croston": 0.6},
    "intermittent": {"croston": 1.0, "arima": 0.5},
    "lumpy": {"croston": 1.0},
}


def guardrail_penalty(df: pd.DataFrame, result: EngineResult) -> float:
    """
    Guardrail sederhana (MVP): forecast yang rata-ratanya melenceng jauh dari
    skala historis (indikasi bias sistematis) kena penalti lebih besar.

    TODO (Post-MVP): ganti dengan tracking signal formal begitu EngineResult
    menyertakan actual-vs-predicted per periode holdout, bukan hanya MASE agregat.
    """
    historical = to_daily_series(df)
    hist_mean = historical.mean()
    hist_std = historical.std() or 1.0

    if not result.forecast:
        return 1.0  # tidak ada forecast sama sekali → penalti maksimum

    forecast_mean = sum(p.value for p in result.forecast) / len(result.forecast)
    bias_ratio = abs(forecast_mean - hist_mean) / hist_std
    return float(min(1.0, bias_ratio / 3))


def compute_score(mase: float, guardrail_pen: float, profile: DemandProfile, method_name: str) -> float:
    settings = get_settings()
    safe_mase = mase if math.isfinite(mase) else 1e6
    mase_score = 1 / (1 + safe_mase)
    fit_score = QUADRANT_FIT_SCORE.get(profile.demand_class, {}).get(method_name, 0.3)

    return (
        settings.SCORING_WEIGHT_MASE * mase_score
        + settings.SCORING_WEIGHT_GUARDRAIL * (1 - guardrail_pen)
        + settings.SCORING_WEIGHT_FIT * fit_score
    )
