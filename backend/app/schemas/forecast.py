"""
Pydantic schemas untuk endpoint forecast — docs/ARCHITECTURE.md §5/§6.8.
"""
from pydantic import BaseModel


class HistoryPoint(BaseModel):
    date: str
    quantity: float


class ForecastRequest(BaseModel):
    history: list[HistoryPoint]
    horizon: int
    method: str | None = None  # None/absen = mode otomatis; diisi = mode manual (§6.8)


class ForecastPointOut(BaseModel):
    date: str
    value: float
    lower: float
    upper: float


class ForecastResponseData(BaseModel):
    status: str
    method_used: str | None
    selection_mode: str | None  # "auto" | "manual"
    demand_class: str | None
    mase: float | None
    explanation: str | None
    forecast: list[ForecastPointOut]
