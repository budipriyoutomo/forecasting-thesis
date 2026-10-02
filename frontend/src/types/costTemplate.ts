// Cocok dengan backend/app/schemas/cost_template.py (Fase 10, 2 Oktober 2026).
export type CostItemType = "OVERHEAD" | "STORAGE_ASSET";

export interface CostTemplateItem {
  id: string | null;
  item_type: CostItemType;
  name: string;
  monthly_amount: string | null; // Decimal → string
  purchase_price: string | null;
  salvage_value: string | null;
  useful_life_months: number | null;
  qty: string;
  monthly_cost: string; // turunan server: overhead × qty / depresiasi per bulan
}

export interface CostTemplate {
  id: string;
  name: string;
  description: string | null;
  ordering_cost: string; // S — per kali pesan
  holding_cost: string; // H — per unit per bulan, isian manual
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
}

export interface CostTemplateInput {
  name: string;
  description: string | null;
  ordering_cost: number;
  holding_cost: number;
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
}
