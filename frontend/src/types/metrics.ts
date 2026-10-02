// Cocok dengan backend/app/schemas/metrics.py (Fase 7).
// Nilai Decimal diserialisasi backend sebagai string (envelope AGENTS.md §4).

export interface CostSummary {
  run_id: string;
  total_ordering_cost: string;
  total_holding_cost: string;
  total_inventory_cost: string; // usulan ForecastIQ
  baseline_inventory_cost: string; // existing (planning perusahaan)
  savings_pct: string;
  // Fase 10 (2 Okt 2026) — additive; opsional supaya respons lama tetap valid
  purchase_cost?: string; // Σ kebutuhan material × harga beli — informasi, bukan TIC
  n_materials_without_price?: number;
  cost_source?: "template" | "env"; // sumber S & H
  cost_template_name?: string | null;
}

export type MetricScope = "baseline" | "forecastiq";

export interface InventoryMetric {
  target_type: string; // product | material
  target_id: string;
  scope: MetricScope;
  service_level: string;
  fill_rate: string;
  stock_out_rate: string;
  inventory_turnover: string;
}
