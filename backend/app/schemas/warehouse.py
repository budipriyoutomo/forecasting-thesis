"""
Pydantic schemas endpoint warehouse (v3.0 Fase 6) — docs/ARCHITECTURE.md §4/§5.
"""
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PalletDimension(BaseModel):
    length: float = Field(gt=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)


class WarehouseConfigInput(BaseModel):
    category: str = Field(default="packaging", min_length=1, max_length=100)
    warehouse_area_m2: float = Field(gt=0)
    pallet_dimension: PalletDimension


class WarehouseConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: str
    warehouse_area_m2: Decimal
    pallet_dimension: dict


class WarehouseValidationOut(BaseModel):
    run_id: str
    total_pallet_capacity: Decimal
    total_pallet_required: Decimal
    is_within_capacity: bool
