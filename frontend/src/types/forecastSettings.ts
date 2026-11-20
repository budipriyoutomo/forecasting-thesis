// Master data Pengaturan Forecast (Fase 11.2a).
// Fase 11.15: tidak ada metode pemenang — `display_metrics` hanya mengatur metrik yang
// DITAMPILKAN di hasil forecast; planner memilih metode per produk.
// CR v3.6 §2: "mase" (metrik utama thesis) ditambahkan; kolom MASE selalu tampil di FE walau
// tidak dicentang (lihat lib/metrics.ts metricColumns).
// Pengujian peramalan hanya MAD, MFE, MAPE (keputusan user 21 Nov 2026). MSE & MASE tetap
// ada di respons ForecastResult/Candidate tapi tidak ditampilkan.
export type DisplayMetric = "mad" | "mfe" | "mape";

export interface ForecastSettings {
  display_metrics: DisplayMetric[];
  /** null = belum diatur → seluruh `available_methods` aktif. */
  enabled_methods: string[] | null;
  available_methods: string[];
  es_alpha_grid: number[];
  es_alpha_metric: AlphaMetric;
  ml_grid_search: boolean;
  ml_winsorize: boolean;
  /** Window Moving Average (n periode, 1–12) — pengganti env MOVING_AVERAGE_WINDOW (19 Nov 2026). */
  ma_window: number;
  service_level_pct: number;
  eoq_method: EoqMethod;
  rop_formula: RopFormula;
  order_qty_policy: OrderQtyPolicy;
  updated_by: string | null;
  updated_at: string | null;
}

export type AlphaMetric = "mad" | "mape";
export type EoqMethod = "classic" | "dynamic";
/** Fase 11.9 — standard = μ·L + SS; with_buffer = μ·L + SS + B (default). */
export type RopFormula = "standard" | "with_buffer";
/** Fase 11.9 — order_up_to = max(MOQ, S − stok) (default); eoq = n × EOQ. */
export type OrderQtyPolicy = "eoq" | "order_up_to";

export interface ForecastSettingsInput {
  display_metrics?: DisplayMetric[];
  enabled_methods?: string[] | null;
  es_alpha_grid?: number[];
  es_alpha_metric?: AlphaMetric;
  ml_grid_search?: boolean;
  ml_winsorize?: boolean;
  ma_window?: number;
  service_level_pct?: number;
  eoq_method?: EoqMethod;
  rop_formula?: RopFormula;
  order_qty_policy?: OrderQtyPolicy;
}
