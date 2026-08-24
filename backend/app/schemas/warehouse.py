"""
Pydantic schemas endpoint warehouse (v3.0 Fase 6, redesain 24 Agustus 2026) —
docs/ARCHITECTURE.md §4/§5. Konfigurasi kapasitas kini per PRODUK, angka bebas
(bukan luas gudang × dimensi palet). `uom` free input teks, tanpa master UOM.
"""
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class WarehouseConfigCreate(BaseModel):
    product_id: str = Field(min_length=1)
    capacity_qty: Decimal = Field(gt=0)
    uom: str = Field(min_length=1, max_length=50)


class WarehouseConfigUpdate(BaseModel):
    capacity_qty: Decimal = Field(gt=0)
    uom: str = Field(min_length=1, max_length=50)


class WarehouseConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    product_id: str
    capacity_qty: Decimal
    uom: str


class WarehouseProductValidationOut(BaseModel):
    product_id: str
    required_qty: Decimal
    capacity_qty: Decimal
    is_within_capacity: bool


class WarehouseValidationOut(BaseModel):
    run_id: str
    is_within_capacity: bool
    details: list[WarehouseProductValidationOut]
