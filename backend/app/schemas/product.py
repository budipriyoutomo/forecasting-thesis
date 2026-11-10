"""
Pydantic schemas endpoint products (v3.0) — docs/ARCHITECTURE.md §4/§5.
Fase 10: `selling_price` = harga produk per unit, IDR, opsional. HPP (`cost_price`) dihapus
10 Nov 2026 — field itu di payload lama diabaikan (bukan ditolak).
"""
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    category: str | None = Field(default=None, max_length=100)
    unit: str = Field(min_length=1, max_length=20)
    selling_price: Decimal | None = Field(default=None, ge=0)


class ProductUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = Field(default=None, max_length=100)
    unit: str | None = Field(default=None, min_length=1, max_length=20)
    selling_price: Decimal | None = Field(default=None, ge=0)


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    name: str
    category: str | None
    unit: str
    selling_price: Decimal | None = None
