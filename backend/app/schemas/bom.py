"""
Pydantic schemas endpoint boms (v3.0) — docs/ARCHITECTURE.md §4/§5.
"""
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BomCreate(BaseModel):
    product_id: str = Field(min_length=1)
    material_id: str = Field(min_length=1)
    qty_per_unit: Decimal = Field(gt=0)  # jumlah material per 1 unit produk jadi


class BomBulkItem(BaseModel):
    material_id: str = Field(min_length=1)
    qty_per_unit: Decimal = Field(gt=0)


class BomBulkCreate(BaseModel):
    """19 Nov 2026 — satu produk, banyak material sekaligus (form "Tambah BOM")."""
    product_id: str = Field(min_length=1)
    items: list[BomBulkItem] = Field(min_length=1)

    @model_validator(mode="after")
    def _material_unik(self):
        ids = [i.material_id for i in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("Material yang sama tidak boleh diinput dua kali untuk satu produk.")
        return self


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
    # Fase 10 — read-only: qty_per_unit × materials.unit_price (null bila tanpa harga)
    line_cost: Decimal | None = None
    # 19 Nov 2026 — level BOM: baris `boms` selalu level 1 (produk → material dibeli).
    # Level 2+ ada di `material_components` (GET /material-components).
    level: int = 1
