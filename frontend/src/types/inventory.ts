// Fase 11.1/11.5 — stok ERP & faktor waste (backend/app/api/v1/inventory.py, material_usage.py).
// Kedatangan manual dihapus 20 Nov 2026 — kedatangan = hasil ROP (halaman /material-arrivals).
export interface LatestStock {
  material_id: string;
  snapshot_date: string;
  qty: number;
}

export interface WasteFactor {
  material_id: string;
  waste_factor: number | null;
}
