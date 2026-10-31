"""
Tipe data bersama untuk semua fungsi forecasting engine.

Lihat AGENTS.md §5 dan docs/ARCHITECTURE.md §6.0 — setiap metode forecasting
adalah SATU FUNGSI dengan signature:

    def forecast_<method>(df: pd.DataFrame, horizon: int) -> EngineResult

`df` wajib punya kolom `date` (datetime-like) dan `quantity` (numeric),
sudah diurutkan menaik berdasarkan tanggal, untuk SATU material.
"""
from dataclasses import dataclass, field

import pandas as pd

# Grid α Exponential Smoothing thesis (docx "Rumus thesis untuk program"):
# data stabil 0,01/0,05/0,15/0,2 · data bergejolak 0,8/0,95/0,99.
THESIS_ALPHA_GRID: tuple[float, ...] = (0.01, 0.05, 0.15, 0.2, 0.8, 0.95, 0.99)


@dataclass
class ForecastPoint:
    date: str
    value: float
    lower: float
    upper: float


@dataclass
class EngineResult:
    """
    Hasil satu metode forecasting (v3.0).

    Metrik akurasi holdout backtest: MAD/MFE/MSE/MAPE (Bab III thesis).
    `mase` opsional (COMPUTE_MASE) — metrik tambahan, BUKAN dipakai ranking default.
    Engine legacy v2.0 hanya mengisi `mase` (mad/mfe/mse/mape tetap NaN default).
    """
    forecast: list[ForecastPoint]
    explanation: str
    mad: float = float("nan")
    mfe: float = float("nan")
    mse: float = float("nan")
    mape: float = float("nan")
    mase: float | None = None
    # Fase 11.2: RF/XGB → {fitur: bobot ternormalisasi}, terurut menurun. Lainnya None.
    feature_importance: dict[str, float] | None = None
    # Parameter yang benar-benar dipakai (α ES, hasil grid search ML, outlier di-cap, ...).
    hyperparameters: dict | None = None


@dataclass
class EngineOptions:
    """Opsi engine dari master data Pengaturan Forecast (Fase 11.2) — argumen opsional
    ketiga `forecast_<method>(df, horizon, options=None)`; None = default thesis."""

    es_alpha_grid: tuple[float, ...] = THESIS_ALPHA_GRID
    es_alpha_metric: str = "mad"  # mad | mape — metrik pemilihan α (thesis: MAD)
    ml_grid_search: bool = False  # GridSearchCV + TimeSeriesSplit untuk RF/XGB
    ml_winsorize: bool = False  # cap outlier IQR sebelum training ML
    # Fase 11.2b: variabel eksternal aktif — index = periode (histori + horizon),
    # kolom = kode variabel. None/kosong = tanpa variabel eksternal.
    exog: pd.DataFrame | None = field(default=None, repr=False)
