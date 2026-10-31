// Cocok dengan backend/app/schemas/reorder.py
export type ReorderStatus = "urgent" | "safe" | "overstock";

export interface ReorderRecommendation {
  material_id: string;
  safety_stock: string; // Decimal sebagai string
  reorder_point: string;
  recommended_order_qty: string;
  status: ReorderStatus;
  // Fase 11 — additive (opsional supaya respons lama tetap valid)
  buffer_stock?: string | null; // max(0, faktor waste − 1) × kebutuhan periode
  waste_factor?: string | null; // Σ aktual ÷ Σ standar pemakaian
  eoq_qty?: string | null;
  eoq_method?: "classic" | "dynamic" | null;
  item_status?: "COMPLETED" | "MISSING_UNIT_PRICE" | "MISSING_HOLDING_RATE" | null;
  annual_demand?: string | null;
  current_stock_used?: string | null;
  stock_source?: "snapshot" | "request" | null;
}
