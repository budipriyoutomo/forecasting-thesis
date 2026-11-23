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
  // Fase 11.17 — adjust kapasitas gudang: nilai sistem sebelum adjust (null = tidak di-adjust)
  safety_stock_system?: string | null;
  buffer_stock_system?: string | null;
  service_level_effective?: string | null; // α efektif (%) = Φ(SS ÷ σ·√L)
  adjustment_source?: "suggested" | "custom" | null;
  // CR v3.5 §5.4 — rincian biaya persediaan per material (Decimal → string; null = belum dihitung)
  ordering_cost?: string | null; // biaya pesan setahun (A/Q)·S
  holding_cost?: string | null; // biaya simpan setahun
  total_inventory_cost?: string | null; // TIC = pesan + simpan
  unit_price_used?: string | null; // C, harga material saat hitung
  holding_rate_used?: string | null; // i (%) tahunan; hanya EOQ klasik
  // 23 Nov 2026 — input perhitungan SS/ROP/EOQ yang dipakai backend (null = rekomendasi lama;
  // jalankan ulang perencanaan). Hanya untuk MENAMPILKAN perhitungan — rumus tetap di backend.
  mu_period?: string | null; // μ kebutuhan per periode (MRP)
  sigma_period?: string | null; // σ kebutuhan per periode (ddof 1)
  period_days?: string | null; // hari per periode (bulanan ≈ 30/31)
  lead_time_days_used?: string | null; // L (hari)
  z_value?: string | null; // Z = Φ⁻¹(service level)
  service_level_pct_used?: string | null; // target service level (%)
  eoq_raw_qty?: string | null; // EOQ hasil rumus sebelum pembulatan MOQ
  ordering_cost_per_order?: string | null; // S, biaya pesan per pesanan (Rp)
  holding_cost_per_unit?: string | null; // H, biaya simpan per unit per periode (EOQ dinamis)
}
