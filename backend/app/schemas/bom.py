"""
Pydantic schemas endpoint boms (v3.0) — docs/ARCHITECTURE.md §4/§5.
"""
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class BomCreate(BaseModel):
    product_id: str = Field(min_length=1)
    material_id: str = Field(min_length=1)
    qty_per_unit: Decimal = Field(gt=0)  # jumlah material per 1 unit produk jadi


class BomUpdate(BaseModel):
    product_id: str | None = Field(default=None, min_length=1)
    material_id: str | None = Field(default=None, min_length=1)
    qty_per_unit: Decimal | None = Field(default=None, gt=0)


class BomResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    product_id: str
    material_id: str
    qty_per_unit: Decimal
