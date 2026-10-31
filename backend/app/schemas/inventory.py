"""Schemas stok & kedatangan material (Fase 11.5) — docs/ARCHITECTURE.md §5."""
from datetime import date

from pydantic import BaseModel, Field


class MaterialReceiptCreate(BaseModel):
    material_id: str
    expected_date: date
    qty: float = Field(gt=0)
    note: str | None = None


class MaterialReceiptUpdate(BaseModel):
    expected_date: date | None = None
    qty: float | None = Field(default=None, gt=0)
    note: str | None = None
