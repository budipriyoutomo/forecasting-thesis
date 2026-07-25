"""
Tipe data bersama untuk semua fungsi forecasting engine.

Lihat AGENTS.md §5 dan docs/ARCHITECTURE.md §6.0 — setiap metode forecasting
adalah SATU FUNGSI dengan signature:

    def forecast_<method>(df: pd.DataFrame, horizon: int) -> EngineResult

`df` wajib punya kolom `date` (datetime-like) dan `quantity` (numeric),
sudah diurutkan menaik berdasarkan tanggal, untuk SATU material.
"""
from dataclasses import dataclass


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
