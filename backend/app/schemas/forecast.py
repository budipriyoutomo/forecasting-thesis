"""
Pydantic schemas untuk endpoint forecast — docs/ARCHITECTURE.md §5/§6.8.
"""
from pydantic import BaseModel, Field


class ForecastRunRequest(BaseModel):
    """POST /api/v1/forecast/runs — banyak material sekaligus (§6.8).

    `method` None/absen → mode otomatis (Auto Model Selection).
    `method` diisi → mode manual (dipaksa ke seluruh material di run ini).
    """

    material_ids: list[str] = Field(min_length=1)
    horizon: int = Field(gt=0)
    horizon_unit: str = "days"
    method: str | None = None


class ForecastPointOut(BaseModel):
    date: str
    value: float
    lower: float
    upper: float


class ForecastRunSummary(BaseModel):
    run_id: str
    status: str  # PENDING / PROCESSING / COMPLETED / FAILED
    horizon: int
    horizon_unit: str
    n_materials: int
    n_completed: int
    n_failed: int


class ForecastResultOut(BaseModel):
    material_id: str
    status: str  # COMPLETED / INSUFFICIENT_DATA / MODEL_SELECTION_FAILED
    method_used: str | None = None
    selection_mode: str | None = None
    demand_class: str | None = None
    mase: float | None = None
    explanation: str | None = None
    forecast: list[ForecastPointOut] = []
    metrics: dict | None = None
