"""
Pydantic schemas endpoint warehouse (v3.0 Fase 6, redesain 24 Agustus 2026) —
docs/ARCHITECTURE.md §4/§5. Konfigurasi kapasitas per PRODUK.

Fase 10 (2 Oktober 2026): request berisi input pallet/dus; `capacity_qty`, `uom`, dan
`capacity_dus` hanya ada di response (turunan server). Validasi silang mode × unit
produk dilakukan service (`WAREHOUSE_CAPACITY_INVALID`), bukan di sini.
"""
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CapacityMode = Literal["PALLET", "DUS", "COMBINED"]


class WarehouseConfigUpdate(BaseModel):
    capacity_mode: CapacityMode
    pallet_qty: Decimal = Decimal(0)
    dus_qty: Decimal = Decimal(0)
    dus_per_pallet: Decimal | None = None
    pcs_per_dus: Decimal | None = None


class WarehouseConfigCreate(WarehouseConfigUpdate):
    product_id: str = Field(min_length=1)


class WarehouseConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    product_id: str
    capacity_mode: CapacityMode
    pallet_qty: Decimal
    dus_qty: Decimal
    dus_per_pallet: Decimal | None
    pcs_per_dus: Decimal | None
    capacity_dus: Decimal
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
