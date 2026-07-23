"""
Registry — dict[str, Callable], BUKAN class registry (lihat AGENTS.md §5).
Tidak ada factory.py terpisah karena setiap engine adalah fungsi stateless;
"instansiasi" tidak diperlukan, cukup lookup nama → fungsi.
"""
from typing import Callable

import pandas as pd

from app.config import get_settings
from app.services.forecasting.classification import DemandProfile
from app.services.forecasting.engines.arima_engine import forecast_arima
from app.services.forecasting.engines.croston_engine import forecast_croston
from app.services.forecasting.engines.ets_engine import forecast_ets
from app.services.forecasting.engines.lightgbm_engine import forecast_lightgbm

# from app.services.forecasting.engines.prophet_engine import forecast_prophet  # TODO: belum siap, lihat file-nya
from app.services.forecasting.types import EngineResult

MODEL_REGISTRY: dict[str, Callable[[pd.DataFrame, int], EngineResult]] = {
    "ets": forecast_ets,
    "arima": forecast_arima,
    "lgbm": forecast_lightgbm,
    "croston": forecast_croston,
}

# Kuadran mana yang boleh dipertimbangkan di mode OTOMATIS (docs/ARCHITECTURE.md §6.3).
# Mode manual tidak dibatasi peta ini — user boleh memilih metode apapun yang aktif.
QUADRANT_CANDIDATE_MAP: dict[str, list[str]] = {
    "smooth": ["ets", "arima"],
    "erratic": ["lgbm", "croston"],
    "intermittent": ["croston", "arima"],
    "lumpy": ["croston"],
}


def get_enabled_methods() -> set[str]:
    settings = get_settings()
    enabled_in_env = {name.strip() for name in settings.FORECAST_ENGINES_ENABLED.split(",") if name.strip()}
    return enabled_in_env & MODEL_REGISTRY.keys()  # abaikan nama di env yang belum ada fungsinya (mis. "prophet")


def filter_candidates(profile: DemandProfile) -> list[str]:
    """Kandidat untuk mode OTOMATIS — sesuai kuadran demand & yang aktif di env."""
    enabled = get_enabled_methods()
    return [name for name in QUADRANT_CANDIDATE_MAP[profile.demand_class] if name in enabled]
