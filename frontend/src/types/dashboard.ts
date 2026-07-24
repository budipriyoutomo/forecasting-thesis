// Cocok dengan backend/app/services/dashboard_service.py summary()
export interface DashboardSummary {
  n_materials: number;
  latest_run: {
    run_id: string;
    status: string;
    n_materials: number;
    n_completed: number;
    n_failed: number;
    avg_mase: number | null;
  } | null;
  reorder_status_counts: {
    urgent: number;
    safe: number;
    overstock: number;
  };
  n_recent_overrides: number;
}
