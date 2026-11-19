"""
Pydantic schemas adjust kapasitas gudang (Fase 11.17) — docs/ARCHITECTURE.md §4/§5.
SS & Buffer disimpan sebagai qty absolut (unit material); `service_level_pct` hanya informasi
anak tangga usulan. Alasan wajib untuk `custom` divalidasi service (OVERRIDE_REASON_REQUIRED).
"""
from typing import Literal

from pydantic import BaseModel, Field


class CapacityAdjustmentItem(BaseModel):
    material_id: str
    safety_stock: float = Field(ge=0)
    buffer_stock: float = Field(ge=0)
    service_level_pct: float | None = Field(default=None, gt=50, lt=100)


class CapacityAdjustmentCreateRequest(BaseModel):
    source: Literal["suggested", "custom"]
    items: list[CapacityAdjustmentItem] = Field(min_length=1)
    reason: str | None = None


class CapacityAdjustmentResetRequest(BaseModel):
    reason: str | None = None


class CapacityAdjustmentOut(BaseModel):
    id: str
    run_id: str
    material_id: str
    user_id: str
    source: str
    service_level_pct: float | None
    safety_stock: float | None
    buffer_stock: float | None
    previous_value: dict | None
    reason: str
    created_at: str | None = None
