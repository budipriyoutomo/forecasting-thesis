// Cocok dengan backend/app/services/dashboard_service.py summary()

export interface DashboardMetricScope {
  service_level: number | null;
  fill_rate: number | null;
  stock_out_rate: number | null;
  inventory_turnover: number | null;
}

export interface DashboardSummary {
  n_materials: number;
  latest_run: {
    run_id: string;
    status: string;
    n_products: number; // jumlah forecast_results = produk (CR v3.5 §4)
    n_completed: number;
    n_failed: number;
    avg_mase: number | null;
    avg_mape: number | null; // Fase 9
    avg_mad?: number | null; // 21 Nov 2026 — tile akurasi (MAD/MFE/MAPE)
    avg_mfe?: number | null;
    total_inventory_cost: number; // Fase 9
    // CR v3.6 §1/§3 — additive (opsional: respons lama)
    created_at?: string | null;
    created_by?: string | null;
    n_pending_selection?: number;
    total_inventory_cost_baseline?: number | null;
    savings_pct?: number | null;
  } | null;
  reorder_status_counts: {
    urgent: number;
    safe: number;
    overstock: number;
  };
  n_recent_overrides: number;
  // Fase 9 (additive) — null bila belum ada validasi/metrik untuk run terakhir.
  // Kapasitas per produk (redesain 24 Agustus 2026) — ringkasan jumlah produk
  // yang melebihi kapasitasnya, bukan lagi agregat palet.
  warehouse: {
    is_within_capacity: boolean;
    n_products_over: number;
    n_products_checked: number;
    /** CR v3.6 §3 — maks 10, kelebihan terbesar dulu. */
    products_over?: DashboardProductOver[];
  } | null;
  inventory_metrics: Record<string, DashboardMetricScope> | null;
  /** CR v3.6 §3 — daftar "Butuh perhatian"; null bila belum ada run. */
  attention?: DashboardAttention | null;
}

export interface DashboardProductOver {
  product_id: string;
  code: string | null;
  name: string | null;
  excess_qty: number;
}

export interface DashboardAttention {
  n_failed_products: number;
  n_missing_cost_data: number;
  n_shortage_periods: number;
}
