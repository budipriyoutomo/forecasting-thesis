// Fase 11.6/11.8 — proyeksi stok material & ringkasan pipeline (backend/app/api/v1/stock_projection.py, planning.py)
export type ProjectionScenario = "proposed" | "baseline";

export interface StockProjectionRow {
  material_id: string;
  scenario: ProjectionScenario;
  period: string;
  opening_qty: number;
  receipt_qty: number;
  usage_qty: number;
  order_qty: number;
  ending_qty: number;
  shortage_qty: number;
  capacity_qty: number | null;
  utilization_opening_pct: number | null;
  utilization_ending_pct: number | null;
  is_within_capacity: boolean | null;
}

export interface PlanningSummary {
  reorder: { n_materials: number; n_urgent: number; n_missing_data: number };
  projection: { n_rows: number; n_over_capacity: number; n_shortage_periods: number; baseline_available: boolean };
  evaluation: { n_material_metrics: number; n_product_metrics: number };
  cost: {
    total_inventory_cost: number | null;
    baseline_inventory_cost: number | null;
    savings_pct: number | null;
    shortage_cost: number | null;
    baseline_shortage_cost: number | null;
    eoq_method: string | null;
  };
}
