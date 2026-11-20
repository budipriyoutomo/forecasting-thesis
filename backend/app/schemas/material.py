"""
Pydantic schemas untuk endpoint materials — docs/ARCHITECTURE.md §4/§5.
"""
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


_DIMENSION_DEPRECATED = "Tidak dipakai perhitungan apa pun (CR v3.5 §5.5); hanya disimpan untuk kompatibilitas."


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
    # DEPRECATED (CR v3.5 §5.5, 20 Nov 2026): tidak dipakai perhitungan apa pun sejak
    # kapasitas gudang per produk / grup material. Tetap diterima & disimpan agar kontrak
    # API dan import CSV (kolom length/width/height) tidak putus; kolom DB tidak di-drop.
    dimension: Dimension | None = Field(default=None, deprecated=_DIMENSION_DEPRECATED)
    # Fase 10 — harga beli per unit, IDR, opsional
    unit_price: Decimal | None = Field(default=None, ge=0)


class MaterialUpdate(BaseModel):
    # Semua opsional — partial update. Kode tidak boleh diubah jadi kosong.
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = Field(default=None, max_length=100)
    unit: str | None = Field(default=None, min_length=1, max_length=20)
    lead_time_days: int | None = Field(default=None, ge=0)
    moq: Decimal | None = Field(default=None, ge=0)
    manual_safety_stock: Decimal | None = Field(default=None, ge=0)
    dimension: Dimension | None = Field(default=None, deprecated=_DIMENSION_DEPRECATED)
    unit_price: Decimal | None = Field(default=None, ge=0)


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
    dimension: dict | None = None  # deprecated (CR v3.5 §5.5) — tetap dikirim agar kontrak tidak putus
    unit_price: Decimal | None = None
