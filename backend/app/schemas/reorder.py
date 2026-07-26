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
    material_id: str
    safety_stock: Decimal
    reorder_point: Decimal
    recommended_order_qty: Decimal
    status: str  # urgent / safe / overstock
    # v3.0 — buffer stock, EOQ dinamis & total biaya (opsional; null bila belum dihitung)
    buffer_stock: Decimal | None = None
    eoq_qty: Decimal | None = None
    ordering_cost: Decimal | None = None
    holding_cost: Decimal | None = None
    total_inventory_cost: Decimal | None = None
