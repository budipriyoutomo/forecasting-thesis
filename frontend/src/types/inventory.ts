// Fase 11.1/11.5 — stok ERP, kedatangan material, faktor waste (backend/app/api/v1/inventory.py, material_usage.py)
export interface LatestStock {
  material_id: string;
  snapshot_date: string;
  qty: number;
}

export interface MaterialReceipt {
  id: string;
  material_id: string;
  expected_date: string;
  qty: number;
  source: "manual" | "upload";
  note: string | null;
}

export interface MaterialReceiptInput {
  material_id: string;
  expected_date: string;
  qty: number;
  note: string | null;
}

export interface WasteFactor {
  material_id: string;
  waste_factor: number | null;
}
