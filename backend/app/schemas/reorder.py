"""
Pydantic schemas untuk endpoint reorder — docs/ARCHITECTURE.md §4/§5.
"""
from decimal import Decimal

from pydantic import BaseModel, Field


class ReorderGenerateRequest(BaseModel):
    run_id: str
    # Stok saat ini per material (opsional) — menentukan status urgent/safe/overstock.
    # Default 0 kalau tidak dikirim (dianggap perlu reorder).
    current_stock: dict[str, float] = Field(default_factory=dict)


class ReorderRecommendationOut(BaseModel):
    id: str | None = None  # target_id untuk override planner (v3.3)
    material_id: str
    safety_stock: Decimal
    reorder_point: Decimal
    recommended_order_qty: Decimal
    status: str  # urgent / safe / overstock
    # v3.0 — buffer stock, EOQ dinamis & total biaya (opsional; null bila belum dihitung)
    buffer_stock: Decimal | None = None
    waste_factor: Decimal | None = None
    eoq_method: str | None = None  # Fase 11.4 — classic | dynamic
    item_status: str | None = None  # COMPLETED | MISSING_UNIT_PRICE | MISSING_HOLDING_RATE
    annual_demand: Decimal | None = None
    unit_price_used: Decimal | None = None
    holding_rate_used: Decimal | None = None
    current_stock_used: Decimal | None = None
    stock_source: str | None = None  # snapshot | request
    eoq_qty: Decimal | None = None
    ordering_cost: Decimal | None = None
    holding_cost: Decimal | None = None
    total_inventory_cost: Decimal | None = None
    # Fase 11.9 (v3.3) — kebijakan pesan yang dipakai; null = rekomendasi sebelum v3.3
    rop_formula_used: str | None = None  # standard | with_buffer
    order_qty_policy_used: str | None = None  # eoq | order_up_to
    order_up_to_level: Decimal | None = None
    moq_used: Decimal | None = None
    # Fase 11.14 — override planner yang BERLAKU untuk (run, material); angka sistem tetap
    # di `recommended_order_qty`. null = belum di-override.
    override_qty: Decimal | None = None
    override_reason: str | None = None
    override_at: str | None = None
