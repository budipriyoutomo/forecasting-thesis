// Cocok dengan backend/app/schemas/forecast.py
export interface ForecastPoint {
  date: string;
  value: number;
  lower: number;
  upper: number;
}

export interface ForecastResult {
  material_id: string;
  status: "COMPLETED" | "INSUFFICIENT_DATA" | "MODEL_SELECTION_FAILED";
  method_used: string | null;
  selection_mode: "auto" | "manual" | null;
  demand_class: string | null;
  mase: number | null;
  explanation: string | null;
  forecast: ForecastPoint[];
  metrics: Record<string, unknown> | null;
}

export interface ForecastRunSummary {
  run_id: string;
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
  horizon: number;
  horizon_unit: string;
  n_materials: number;
  n_completed: number;
  n_failed: number;
}

export interface ForecastRunResponse {
  run: ForecastRunSummary;
  results: ForecastResult[];
}

export interface ForecastRunInput {
  material_ids: string[];
  horizon: number;
  horizon_unit?: string;
  method?: string | null;
}
