"""
Registry v3.0 — dict[str, Callable] datar (AGENTS.md §5). Comparative Selection:
tak ada filter kuadran — seluruh metode aktif ikut dibandingkan (docs §6.3).

Engine legacy v2.0 (ets/arima/lgbm/croston) dipindah ke engines/legacy/ dan
di-comment di bawah — nonaktif default, aktifkan dgn uncomment + FORECAST_ENGINES_ENABLED
(docs/ARCHITECTURE.md §6.9). Jangan hapus file legacy (larangan #16).
"""
from typing import Callable

import pandas as pd

from app.config import get_settings
from app.services.forecasting.engines.exponential_smoothing_engine import (
    forecast_exponential_smoothing,
)
from app.services.forecasting.engines.lstm_engine import forecast_lstm
from app.services.forecasting.engines.moving_average_engine import forecast_moving_average
from app.services.forecasting.engines.random_forest_engine import forecast_random_forest
from app.services.forecasting.engines.xgboost_engine import forecast_xgboost
from app.services.forecasting.types import EngineResult

# Legacy (nonaktif default, uncomment untuk mengaktifkan kembali):
# from app.services.forecasting.engines.legacy.ets_engine import forecast_ets
# from app.services.forecasting.engines.legacy.arima_engine import forecast_arima
# from app.services.forecasting.engines.legacy.lightgbm_engine import forecast_lightgbm
# from app.services.forecasting.engines.legacy.croston_engine import forecast_croston

MODEL_REGISTRY: dict[str, Callable[[pd.DataFrame, int], EngineResult]] = {
    "moving_average": forecast_moving_average,
    "exponential_smoothing": forecast_exponential_smoothing,
    "random_forest": forecast_random_forest,
    "xgboost": forecast_xgboost,
    "lstm": forecast_lstm,
    # "ets": forecast_ets,
    # "arima": forecast_arima,
    # "lgbm": forecast_lightgbm,
    # "croston": forecast_croston,
}


def get_enabled_methods() -> set[str]:
    settings = get_settings()
    enabled_in_env = {name.strip() for name in settings.FORECAST_ENGINES_ENABLED.split(",") if name.strip()}
    return enabled_in_env & MODEL_REGISTRY.keys()  # abaikan nama di env yang belum ada fungsinya
