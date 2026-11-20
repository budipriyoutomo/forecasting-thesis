// Fase 11.1/11.5 — stok ERP & faktor waste (backend/app/api/v1/inventory.py, material_usage.py).
// Kedatangan manual dihapus 20 Nov 2026 — kedatangan = hasil ROP (halaman /material-arrivals).
export interface LatestStock {
  material_id: string;
  snapshot_date: string;
  qty: number;
}

// CR v3.5 §5.2 — riwayat (GET /stock-snapshots, GET /material-usage).
export interface StockSnapshot {
  material_id: string;
  snapshot_date: string;
  qty: number;
  uom: string | null;
}

export interface MaterialUsageRow {
  material_id: string;
  product_id: string | null;
  period: string;
  production_output: number | null;
  standard_usage: number | null;
  actual_usage: number | null;
}

export interface WasteFactor {
  material_id: string;
  waste_factor: number | null;
}
