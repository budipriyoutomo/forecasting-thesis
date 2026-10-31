"""
Registry v3.0 — dict[str, Callable] datar (AGENTS.md §5). Comparative Selection:
tak ada filter kuadran — seluruh metode aktif ikut dibandingkan (docs §6.3).

Engine legacy v2.0 (ets/arima/lgbm/croston) dipindah ke engines/legacy/ dan
di-comment di bawah — nonaktif default, aktifkan dgn uncomment lalu centang di master data
Pengaturan Forecast (docs/ARCHITECTURE.md §6.9). Jangan hapus file legacy (larangan #16).

Fase 11.2a: daftar metode aktif dibaca dari master data `forecast_settings.enabled_methods`
(diteruskan sebagai argumen), BUKAN env. None = belum diatur → seluruh metode terdaftar.
"""
from collections.abc import Iterable
from typing import Callable

import pandas as pd

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


def available_methods() -> list[str]:
    """Seluruh metode yang punya fungsi terdaftar — pilihan di Pengaturan Forecast."""
    return sorted(MODEL_REGISTRY)


def get_enabled_methods(enabled: Iterable[str] | None = None) -> set[str]:
    if enabled is None:
        return set(MODEL_REGISTRY)
    return set(enabled) & MODEL_REGISTRY.keys()  # abaikan nama yang belum ada fungsinya
