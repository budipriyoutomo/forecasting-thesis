"""
Pydantic schemas endpoint /cost-templates (Fase 10, 2 Oktober 2026) —
docs/ARCHITECTURE.md §4/§5/§6.8. Item disimpan nested; PUT mengganti seluruh daftar.
"""
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

CostItemType = Literal["OVERHEAD", "STORAGE_ASSET", "MAINTENANCE"]
PeriodBasis = Literal["monthly", "annual"]


class CostTemplateItemIn(BaseModel):
    item_type: CostItemType
    name: str = Field(min_length=1, max_length=100)
    monthly_amount: Decimal | None = Field(default=None, ge=0)  # OVERHEAD/MAINTENANCE, nominal per period_basis
    period_basis: PeriodBasis = "monthly"  # Fase 11.4 — annual: nominal tahunan (÷ 12)
    purchase_price: Decimal | None = Field(default=None, ge=0)  # STORAGE_ASSET
    salvage_value: Decimal | None = Field(default=None, ge=0)
    useful_life_months: int | None = Field(default=None, gt=0)
    qty: Decimal = Field(default=Decimal(1), gt=0)

    @model_validator(mode="after")
    def _required_by_type(self):
        if self.item_type in ("OVERHEAD", "MAINTENANCE"):
            if self.monthly_amount is None:
                raise ValueError("Overhead/perawatan wajib punya nominal biaya (monthly_amount).")
        else:
            if self.purchase_price is None or self.useful_life_months is None:
                raise ValueError("Aset penyimpanan wajib punya harga beli & umur ekonomis (bulan).")
            if self.salvage_value is not None and self.salvage_value > self.purchase_price:
                raise ValueError("Nilai sisa tidak boleh melebihi harga beli.")
        return self


class CostTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    ordering_cost: Decimal = Field(ge=0)  # S — per kali pesan
    holding_cost: Decimal = Field(ge=0)  # H — per unit per bulan, isian manual
    holding_cost_rate_pct: Decimal | None = Field(default=None, gt=0, le=100)  # i (%) tahunan, EOQ klasik
    items: list[CostTemplateItemIn] = Field(default_factory=list)


# PUT = ganti penuh (termasuk items), jadi bentuknya sama dengan create.
CostTemplateUpdate = CostTemplateCreate


class CostTemplateItemOut(BaseModel):
    id: str | None
    item_type: CostItemType
    name: str
    monthly_amount: Decimal | None
    purchase_price: Decimal | None
    salvage_value: Decimal | None
    useful_life_months: int | None
    qty: Decimal
    period_basis: PeriodBasis = "monthly"
    monthly_cost: Decimal  # turunan: overhead × qty, atau depresiasi garis lurus per bulan


class CostTemplateOut(BaseModel):
    id: str
    name: str
    description: str | None
    ordering_cost: Decimal
    holding_cost: Decimal
    holding_cost_rate_pct: Decimal | None = None
    is_active: bool
    items: list[CostTemplateItemOut]


class CostTemplateSummaryOut(BaseModel):
    template_id: str
    total_depreciation_monthly: Decimal
    total_overhead_monthly: Decimal
    total_monthly: Decimal
    total_capacity_dus: Decimal
    suggested_holding_cost: Decimal | None  # referensi saja — EOQ pakai holding_cost
    holding_cost: Decimal
    total_maintenance_monthly: Decimal = Decimal(0)
    total_annual: Decimal = Decimal(0)
    avg_inventory_value: Decimal | None = None  # dari stock snapshot terakhir × harga material
    suggested_holding_rate_pct: Decimal | None = None  # Keputusan #5 — saran i (%)
    holding_cost_rate_pct: Decimal | None = None
