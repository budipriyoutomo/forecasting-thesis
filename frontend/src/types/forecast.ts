// Cocok dengan backend/app/schemas/forecast.py
export interface ForecastPoint {
  date: string;
  value: number;
  lower: number;
  upper: number;
}

// Satu metode yang ikut dibandingkan di mode otomatis (Comparative Selection).
// Mode manual mengisi satu entri saja: metode yang dipaksa user.
export interface ForecastCandidate {
  method: string;
  mad: number | null;
  mfe: number | null;
  mse: number | null;
  mape: number | null;
  mase: number | null;
}

export interface ForecastResult {
  product_id: string;
  status: "COMPLETED" | "INSUFFICIENT_DATA" | "MODEL_SELECTION_FAILED";
  method_used: string | null;
  selection_mode: "auto" | "manual" | null;
  mad: number | null;
  mfe: number | null;
  mse: number | null;
  mape: number | null;
  mase: number | null;
  candidates_evaluated: ForecastCandidate[] | null;
  explanation: string | null;
  forecast: ForecastPoint[];
  metrics: Record<string, unknown> | null;
}

export interface ForecastRunSummary {
  run_id: string;
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
  horizon: number;
  horizon_unit: string;
  n_products: number;
  n_completed: number;
  n_failed: number;
}

export interface ForecastRunResponse {
  run: ForecastRunSummary;
  results: ForecastResult[];
}

export interface ForecastRunInput {
  product_ids: string[];
  horizon: number;
  horizon_unit?: string;
  method?: string | null;
}

// Hasil breakdown BOM per run. Nilai Decimal diserialisasi backend sebagai string.
// `id` = target_id saat override dengan target_type "material_requirement".
export interface MaterialRequirement {
  id: string;
  run_id: string;
  material_id: string;
  forecast_qty: string;
  standard_usage_qty: string | null;
  actual_usage_qty: string | null;
  buffer_stock_pct: string | null;
}
