// Cocok dengan backend/app/schemas/reorder.py
export type ReorderStatus = "urgent" | "safe" | "overstock";

export interface ReorderRecommendation {
  id?: string | null; // target_id override planner (v3.3); null = respons lama
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
  // Fase 11.9 — kebijakan pesan yang dipakai (null = rekomendasi sebelum v3.3)
  rop_formula_used?: "standard" | "with_buffer" | null;
  order_qty_policy_used?: "eoq" | "order_up_to" | null;
  order_up_to_level?: string | null;
  moq_used?: string | null;
  // Fase 11.14 — override planner yang berlaku untuk (run, material); null = belum di-override
  override_qty?: string | null;
  override_reason?: string | null;
  override_at?: string | null;
}
