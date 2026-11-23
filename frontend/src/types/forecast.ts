// Cocok dengan backend/app/schemas/forecast.py
export interface ForecastPoint {
  date: string;
  value: number;
  lower: number;
  upper: number;
}

// Satu metode yang dijalankan di mode otomatis. Sejak 23 Nov 2026 membawa peringkat pengujian
// (rank 1 = metode terbaik pilihan sistem); run Fase 11.15 tidak punya rank.
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
  /** Peringkat akhir (1 = terbaik, prioritas MAD → MAPE → MFE). Absen di run sebelum 23 Nov 2026. */
  rank?: number;
  rank_mad?: number;
  rank_mfe?: number;
  rank_mape?: number;
}

/** Baris peringkat di analisis pemilihan (nilai metrik sudah dibersihkan dari NaN/inf → null). */
export interface SelectionRankingRow {
  method: string;
  rank: number;
  rank_mad?: number;
  rank_mfe?: number;
  rank_mape?: number;
  mad: number | null;
  mfe: number | null;
  mape: number | null;
  /** Cakupan global: jumlah produk yang dirata-rata untuk metode ini. */
  n_products?: number;
}

/** 23 Nov 2026 — kenapa sistem memilih metode terbaik (mode otomatis). */
export interface SelectionAnalysis {
  /** "global" = satu metode untuk seluruh produk dari RATA-RATA pengujian (23 Nov 2026); run lama tanpa field. */
  scope?: "global" | "product";
  /** Jumlah produk yang dirata-rata. */
  n_products?: number;
  /** Metode yang tidak dibandingkan karena gagal/tidak berlaku di sebagian produk. */
  excluded_methods?: string[];
  /** Diisi bila metode global gagal di produk ini → produk memakai metode terbaiknya sendiri. */
  fallback_reason?: string | null;
  best_method: string;
  /** Urutan prioritas pengujian yang dipakai (snapshot Pengaturan Forecast saat run): MAD → MAPE → MFE. */
  criteria: ("mad" | "mfe" | "mape")[];
  /** Metrik yang memisahkan metode terbaik dari peringkat 2; null = satu kandidat / seri total. */
  decided_by?: "mad" | "mfe" | "mape" | null;
  ranking: SelectionRankingRow[];
  summary: string;
  reasons: string[];
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
  /** 23 Nov 2026 — analisis pemilihan metode terbaik; null untuk mode manual / run lama / gagal. */
  selection_analysis?: SelectionAnalysis | null;
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
  /** Produk yang metodenya belum dipilih (hanya run Fase 11.15; run baru dipilih otomatis). */
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
  /** UI tidak lagi mengirim (sistem memilih metode terbaik); dipertahankan untuk kompatibilitas API. */
  method?: string | null;
}
