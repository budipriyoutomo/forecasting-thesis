// Master data Pengaturan Forecast (Fase 11.2a).
// Fase 11.15: tidak ada metode pemenang — `display_metrics` hanya mengatur metrik yang
// DITAMPILKAN di hasil forecast; planner memilih metode per produk.
export type DisplayMetric = "mad" | "mfe" | "mse" | "mape";

export interface ForecastSettings {
  display_metrics: DisplayMetric[];
  /** null = belum diatur → seluruh `available_methods` aktif. */
  enabled_methods: string[] | null;
  available_methods: string[];
  es_alpha_grid: number[];
  es_alpha_metric: AlphaMetric;
  ml_grid_search: boolean;
  ml_winsorize: boolean;
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
  service_level_pct?: number;
  eoq_method?: EoqMethod;
  rop_formula?: RopFormula;
  order_qty_policy?: OrderQtyPolicy;
}
