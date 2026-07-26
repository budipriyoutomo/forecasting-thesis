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
    n_materials: number;
    n_completed: number;
    n_failed: number;
    avg_mase: number | null;
    avg_mape: number | null; // Fase 9
    total_inventory_cost: number; // Fase 9
  } | null;
  reorder_status_counts: {
    urgent: number;
    safe: number;
    overstock: number;
  };
  n_recent_overrides: number;
  // Fase 9 (additive) — null bila belum ada validasi/metrik untuk run terakhir.
  warehouse: {
    is_within_capacity: boolean;
    total_pallet_required: number;
    total_pallet_capacity: number;
  } | null;
  inventory_metrics: Record<string, DashboardMetricScope> | null;
}
