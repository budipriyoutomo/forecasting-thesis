"""
Pydantic schemas untuk endpoint materials — docs/ARCHITECTURE.md §4/§5.
"""
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class Dimension(BaseModel):
    # float (bukan Decimal) supaya aman diserialisasi ke kolom JSONB
    length: float = Field(gt=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)


class MaterialCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    category: str | None = Field(default=None, max_length=100)
    unit: str = Field(min_length=1, max_length=20)
    lead_time_days: int = Field(default=0, ge=0)
    moq: Decimal = Field(default=Decimal(0), ge=0)
    manual_safety_stock: Decimal | None = Field(default=None, ge=0)
    # v3.0 — kapasitas gudang (docs §6.7)
    dimension: Dimension | None = Field(default=None)
    qty_per_pallet: Decimal | None = Field(default=None, gt=0)


class MaterialUpdate(BaseModel):
    # Semua opsional — partial update. Kode tidak boleh diubah jadi kosong.
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = Field(default=None, max_length=100)
    unit: str | None = Field(default=None, min_length=1, max_length=20)
    lead_time_days: int | None = Field(default=None, ge=0)
    moq: Decimal | None = Field(default=None, ge=0)
    manual_safety_stock: Decimal | None = Field(default=None, ge=0)
    dimension: Dimension | None = Field(default=None)
    qty_per_pallet: Decimal | None = Field(default=None, gt=0)


class MaterialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    name: str
    category: str | None
    unit: str
    lead_time_days: int
    moq: Decimal
    manual_safety_stock: Decimal | None
    dimension: dict | None = None
    qty_per_pallet: Decimal | None = None
