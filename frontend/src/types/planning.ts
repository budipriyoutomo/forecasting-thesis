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
  // Fase 11.17 — opsional supaya respons lama tetap valid
  capacity?: { n_adjusted_materials: number; suggestion: CapacitySuggestion | null };
  cost: {
    total_inventory_cost: number | null;
    baseline_inventory_cost: number | null;
    savings_pct: number | null;
    shortage_cost: number | null;
    baseline_shortage_cost: number | null;
    eoq_method: string | null;
  };
}

// Fase 11.17 — loop kapasitas gudang → adjust SS & Buffer (backend/app/services/capacity_adjustment_service.py)
export type CapacitySuggestionStatus = "within_capacity" | "adjusted" | "infeasible";
export type OverflowCause = "opening_stock" | "receipts" | "moq" | "cycle_stock";

export interface CapacitySuggestionGroup {
  group: string;
  capacity_qty: number;
  excess_before: number;
  excess_after: number;
  service_level_pct: number;
  status: "adjusted" | "infeasible";
  cause: OverflowCause | null;
}

export interface CapacitySuggestionItem {
  material_id: string;
  group: string | null;
  safety_stock_before: number;
  safety_stock_after: number;
  buffer_stock_before: number;
  buffer_stock_after: number;
  reorder_point_before: number;
  reorder_point_after: number;
  service_level_before: number | null;
  service_level_after: number | null;
  service_level_pct: number | null;
}

export interface CapacitySuggestion {
  status: CapacitySuggestionStatus;
  target_service_level_pct: number;
  iterations: number;
  groups: CapacitySuggestionGroup[];
  items: CapacitySuggestionItem[];
}

export type CapacityAdjustmentSource = "suggested" | "custom" | "reset";

export interface CapacityAdjustment {
  id: string;
  run_id: string;
  material_id: string;
  user_id: string;
  source: CapacityAdjustmentSource;
  service_level_pct: number | null;
  safety_stock: number | null;
  buffer_stock: number | null;
  previous_value: Record<string, string | null> | null;
  reason: string;
  created_at: string | null;
}

export interface CapacityAdjustmentInputItem {
  material_id: string;
  safety_stock: number;
  buffer_stock: number;
  service_level_pct?: number | null;
}
