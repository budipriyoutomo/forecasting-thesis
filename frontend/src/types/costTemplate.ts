// Cocok dengan backend/app/schemas/cost_template.py (Fase 10, 2 Oktober 2026).
export type CostItemType = "OVERHEAD" | "STORAGE_ASSET" | "MAINTENANCE";
export type PeriodBasis = "monthly" | "annual";

export interface CostTemplateItem {
  id: string | null;
  item_type: CostItemType;
  name: string;
  monthly_amount: string | null; // Decimal → string
  purchase_price: string | null;
  salvage_value: string | null;
  useful_life_months: number | null;
  qty: string;
  period_basis?: PeriodBasis; // Fase 11.4 — nominal monthly_amount per bulan/tahun
  monthly_cost: string; // turunan server: overhead × qty / depresiasi per bulan
}

export interface CostTemplate {
  id: string;
  name: string;
  description: string | null;
  ordering_cost: string; // S — per kali pesan
  holding_cost: string; // H — per unit per bulan, isian manual
  holding_cost_rate_pct?: string | null; // i (%) tahunan, EOQ klasik (Fase 11.4)
  is_active: boolean;
  items: CostTemplateItem[];
}

export interface CostTemplateItemInput {
  item_type: CostItemType;
  name: string;
  monthly_amount: number | null;
  purchase_price: number | null;
  salvage_value: number | null;
  useful_life_months: number | null;
  qty: number;
  period_basis?: PeriodBasis;
}

export interface CostTemplateInput {
  name: string;
  description: string | null;
  ordering_cost: number;
  holding_cost: number;
  holding_cost_rate_pct?: number | null;
  items: CostTemplateItemInput[];
}

export interface CostTemplateSummary {
  template_id: string;
  total_depreciation_monthly: string;
  total_overhead_monthly: string;
  total_monthly: string;
  total_capacity_dus: string;
  suggested_holding_cost: string | null; // referensi saja — EOQ pakai holding_cost
  holding_cost: string;
  // Fase 11.4/11.5 — saran i (%) = biaya simpan tahunan ÷ rata-rata nilai persediaan
  total_maintenance_monthly?: string;
  total_annual?: string;
  avg_inventory_value?: string | null;
  suggested_holding_rate_pct?: string | null;
  holding_cost_rate_pct?: string | null;
}
