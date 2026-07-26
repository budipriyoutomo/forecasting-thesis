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


class InventoryMetricOut(BaseModel):
    target_type: str  # product / material
    target_id: str
    scope: str  # baseline / forecastiq
    service_level: Decimal
    fill_rate: Decimal
    stock_out_rate: Decimal
    inventory_turnover: Decimal
