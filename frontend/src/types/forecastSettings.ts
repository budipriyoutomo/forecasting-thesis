// Master data Pengaturan Forecast (Fase 11.2a) — metrik penentu metode pemenang.
export type RankingMetric = "mad" | "mfe_abs" | "mape";

export interface ForecastSettings {
  ranking_metric: RankingMetric;
  /** null = belum diatur → seluruh `available_methods` aktif. */
  enabled_methods: string[] | null;
  available_methods: string[];
  es_alpha_grid: number[];
  es_alpha_metric: AlphaMetric;
  ml_grid_search: boolean;
  ml_winsorize: boolean;
  service_level_pct: number;
  eoq_method: EoqMethod;
  updated_by: string | null;
  updated_at: string | null;
}

export type AlphaMetric = "mad" | "mape";
export type EoqMethod = "classic" | "dynamic";

export interface ForecastSettingsInput {
  ranking_metric: RankingMetric;
  enabled_methods?: string[] | null;
  es_alpha_grid?: number[];
  es_alpha_metric?: AlphaMetric;
  ml_grid_search?: boolean;
  ml_winsorize?: boolean;
  service_level_pct?: number;
  eoq_method?: EoqMethod;
}
