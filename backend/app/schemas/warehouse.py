"""
Pydantic schemas endpoint warehouse (v3.0 Fase 6, redesain 24 Agustus 2026) —
docs/ARCHITECTURE.md §4/§5. Konfigurasi kapasitas per PRODUK.

Fase 10 (2 Oktober 2026): request berisi input pallet/dus; `capacity_qty`, `uom`, dan
`capacity_dus` hanya ada di response (turunan server). Validasi silang mode × unit
produk dilakukan service (`WAREHOUSE_CAPACITY_INVALID`), bukan di sini.
"""
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

CapacityMode = Literal["PALLET", "DUS", "COMBINED"]
ItemType = Literal["product", "material"]


class WarehouseConfigUpdate(BaseModel):
    capacity_mode: CapacityMode
    pallet_qty: Decimal = Decimal(0)
    dus_qty: Decimal = Decimal(0)
    dus_per_pallet: Decimal | None = None
    pcs_per_dus: Decimal | None = None


class WarehouseConfigCreate(WarehouseConfigUpdate):
    # Fase 11.6: target produk (default, perilaku lama) atau material — tepat satu id.
    item_type: ItemType = "product"
    product_id: str | None = None
    material_id: str | None = None

    @model_validator(mode="after")
    def _target_sesuai_tipe(self):
        target = self.product_id if self.item_type == "product" else self.material_id
        other = self.material_id if self.item_type == "product" else self.product_id
        if not target or other:
            raise ValueError(f"item_type '{self.item_type}' wajib mengisi tepat {self.item_type}_id.")
        return self


class WarehouseConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    item_type: ItemType = "product"
    product_id: str | None = None
    material_id: str | None = None
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
