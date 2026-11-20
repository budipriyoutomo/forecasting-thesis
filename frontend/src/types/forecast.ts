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
  /** CR v3.6 §7.1 — histori aktual (≤24 periode terakhir) yang dilihat model; [] untuk run lama. */
  history?: HistoryPoint[];
  /** CR v3.6 §7.2 — alasan gagal bahasa natural; null bila sukses / run lama. */
  status_reason?: string | null;
}

export interface HistoryPoint {
  date: string;
  value: number;
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

// GET /forecast/runs — ringkasan run milik user, terbaru dulu (pemilih run, 20 Nov 2026)
export interface ForecastRunListItem {
  run_id: string;
  status: ForecastRunSummary["status"];
  horizon: number;
  horizon_unit: string;
  created_at: string | null;
  created_by?: string | null; // nama/email pembuat run (CR v3.5 §3.4 — semua run terlihat semua role)
  // CR v3.6 §1 — counts per run (opsional: respons sebelum v3.6 tidak membawanya)
  n_products?: number;
  n_completed?: number;
  n_failed?: number;
  n_pending_selection?: number;
  /** Sudah menjalankan pipeline perencanaan (ada proyeksi stok). */
  has_planning?: boolean;
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
