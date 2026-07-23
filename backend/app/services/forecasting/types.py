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
    forecast: list[ForecastPoint]
    mase: float
    explanation: str
