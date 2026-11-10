// Cocok dengan backend/app/schemas/forecast.py
export interface ForecastPoint {
  date: string;
  value: number;
  lower: number;
  upper: number;
}

// Satu metode yang dijalankan di mode otomatis (Fase 11.15: tanpa pemenang & tanpa peringkat).
// Mode manual mengisi satu entri saja: metode yang dipaksa user.
export interface ForecastCandidate {
  method: string;
  mad: number | null;
  mfe: number | null;
  mse: number | null;
  mape: number | null;
  mase: number | null;
  /** Deret forecast metode ini — absen di run sebelum Fase 11.15 (metode tak bisa diganti). */
  forecast?: ForecastPoint[];
  explanation?: string | null;
}

export type SelectionStatus = "SELECTED" | "PENDING_SELECTION";

export interface ForecastResult {
  id: string;
  product_id: string;
  status: "COMPLETED" | "INSUFFICIENT_DATA" | "MODEL_SELECTION_FAILED";
  /** Metode yang BERLAKU (pilihan planner / mode manual / run lama); null = belum dipilih. */
  method_used: string | null;
  /** null untuk hasil gagal. */
  selection_status?: SelectionStatus | null;
  selection_reason?: string | null;
  selected_at?: string | null;
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
  feature_importance?: Record<string, number> | null;
  hyperparameters?: Record<string, unknown> | null;
}

export interface ForecastRunSummary {
  run_id: string;
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
  horizon: number;
  horizon_unit: string;
  n_products: number;
  n_completed: number;
  n_failed: number;
  /** Fase 11.15 — produk yang metodenya belum dipilih planner (dilewati di perencanaan). */
  n_pending_selection?: number;
}

export interface MethodSelectionInput {
  method: string;
  reason: string;
}

export interface RunSelectionResult {
  n_selected: number;
  skipped_product_ids: string[];
  results: ForecastResult[];
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
