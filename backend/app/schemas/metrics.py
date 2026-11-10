"""
Pydantic schemas endpoint Fase 7 — cost-summary & inventory-metrics
(docs/ARCHITECTURE.md §5).
"""
from decimal import Decimal

from pydantic import BaseModel


class CostSummaryOut(BaseModel):
    run_id: str
    total_ordering_cost: Decimal
    total_holding_cost: Decimal
    total_inventory_cost: Decimal  # usulan ForecastIQ
    baseline_inventory_cost: Decimal  # existing (planning)
    savings_pct: Decimal
    # Fase 10 — additive
    purchase_cost: Decimal  # Σ kebutuhan material forecast × harga beli — informasi, bukan bagian TIC
    n_materials_without_price: int
    cost_source: str  # "template" | "env" — sumber S & H
    cost_template_name: str | None
    eoq_method: str = "classic"  # Fase 11.4
    shortage_cost: Decimal | None = None  # Fase 11.7 — Σ material scope forecastiq
    baseline_shortage_cost: Decimal | None = None  # Σ material scope baseline


class InventoryMetricOut(BaseModel):
    target_type: str  # product / material
    target_id: str
    scope: str  # baseline / forecastiq
    service_level: Decimal
    fill_rate: Decimal
    stock_out_rate: Decimal
    inventory_turnover: Decimal
    inventory_days: Decimal | None = None  # Fase 11.7 — turnover dalam hari (thesis)
    shortage_cost: Decimal | None = None  # Fase 11.7 — qty tak terpenuhi × harga produk (selling_price)
