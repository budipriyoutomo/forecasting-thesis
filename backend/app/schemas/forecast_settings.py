"""
Schemas Pengaturan Forecast (Fase 11.2a) — docs/ARCHITECTURE.md §5.
"""
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field

DisplayMetric = Literal["mad", "mfe", "mse", "mape"]  # Fase 11.15 — tampilan, bukan penentu pemenang
AlphaMetric = Literal["mad", "mape"]
EoqMethod = Literal["classic", "dynamic"]
RopFormula = Literal["standard", "with_buffer"]
OrderQtyPolicy = Literal["eoq", "order_up_to"]
Alpha = Annotated[float, Field(gt=0, lt=1)]


class ForecastSettingsUpdate(BaseModel):
    display_metrics: list[DisplayMetric] | None = Field(default=None, min_length=1)  # None = tidak diubah
    enabled_methods: list[str] | None = Field(default=None, min_length=1)  # None = tidak diubah
    es_alpha_grid: list[Alpha] | None = Field(default=None, min_length=1)  # 0 < α < 1
    es_alpha_metric: AlphaMetric | None = None
    ml_grid_search: bool | None = None
    ml_winsorize: bool | None = None
    service_level_pct: float | None = Field(default=None, gt=50, lt=100)
    eoq_method: EoqMethod | None = None
    rop_formula: RopFormula | None = None
    order_qty_policy: OrderQtyPolicy | None = None


class ForecastSettingsOut(BaseModel):
    display_metrics: list[DisplayMetric]  # efektif: tersimpan, atau semua metrik bila belum diatur
    enabled_methods: list[str] | None = None  # None = belum diatur → seluruh available_methods aktif
    available_methods: list[str]  # seluruh metode terdaftar di registry
    es_alpha_grid: list[float]  # efektif: tersimpan, atau grid thesis bila belum diatur
    es_alpha_metric: AlphaMetric
    ml_grid_search: bool
    ml_winsorize: bool
    service_level_pct: float
    eoq_method: EoqMethod
    rop_formula: RopFormula
    order_qty_policy: OrderQtyPolicy
    updated_by: str | None = None
    updated_at: datetime | None = None
