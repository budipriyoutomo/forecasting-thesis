"""
Pydantic schemas endpoint warehouse (v3.0 Fase 6, redesain 24 Agustus 2026) —
docs/ARCHITECTURE.md §4/§5. Konfigurasi kapasitas per PRODUK.

Fase 10 (2 Oktober 2026): request berisi input pallet/dus; `capacity_qty`, `uom`, dan
`capacity_dus` hanya ada di response (turunan server). Validasi silang mode × unit
produk dilakukan service (`WAREHOUSE_CAPACITY_INVALID`), bukan di sini.
"""
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

CapacityMode = Literal["PALLET", "DUS", "COMBINED"]
# 19 Nov 2026: `material` (per item) diganti `material_group` (per grup material).
ItemType = Literal["product", "material_group"]


class WarehouseConfigUpdate(BaseModel):
    capacity_mode: CapacityMode
    pallet_qty: Decimal = Decimal(0)
    dus_qty: Decimal = Decimal(0)
    dus_per_pallet: Decimal | None = None
    pcs_per_dus: Decimal | None = None


class WarehouseConfigCreate(WarehouseConfigUpdate):
    # Target produk (default, perilaku lama) atau grup material — tepat satu target diisi.
    item_type: ItemType = "product"
    product_id: str | None = None
    material_group: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def _target_sesuai_tipe(self):
        group = (self.material_group or "").strip()
        if self.item_type == "product" and (not self.product_id or group):
            raise ValueError("item_type 'product' wajib mengisi product_id saja.")
        if self.item_type == "material_group" and (not group or self.product_id):
            raise ValueError("item_type 'material_group' wajib mengisi material_group saja.")
        return self


class WarehouseConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    item_type: ItemType = "product"
    product_id: str | None = None
    material_id: str | None = None  # legacy (target per material sebelum 19 Nov 2026)
    material_group: str | None = None
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
