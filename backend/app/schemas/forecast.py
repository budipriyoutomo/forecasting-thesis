"""
Pydantic schemas untuk endpoint forecast — docs/ARCHITECTURE.md §5/§6.8.
"""
from pydantic import BaseModel, Field


class ForecastRunRequest(BaseModel):
    """POST /api/v1/forecast/runs — banyak PRODUK jadi sekaligus (§6.6).

    `method` None/absen → mode otomatis (Comparative Selection).
    `method` diisi → mode manual (dipaksa ke seluruh produk di run ini).
    """

    product_ids: list[str] = Field(min_length=1)
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
    n_products: int
    n_completed: int
    n_failed: int


class ForecastResultOut(BaseModel):
    product_id: str
    status: str  # COMPLETED / INSUFFICIENT_DATA / MODEL_SELECTION_FAILED
    method_used: str | None = None
    selection_mode: str | None = None
    mad: float | None = None
    mfe: float | None = None
    mse: float | None = None
    mape: float | None = None
    mase: float | None = None
    candidates_evaluated: list | None = None
    explanation: str | None = None
    forecast: list[ForecastPointOut] = []
    metrics: dict | None = None
