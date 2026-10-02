import type { CostItemType } from "@/types/costTemplate";

export const COST_ITEM_LABELS: Record<CostItemType, string> = {
  OVERHEAD: "Overhead",
  STORAGE_ASSET: "Aset penyimpanan",
};

interface ItemCostInput {
  item_type: CostItemType;
  monthly_amount?: number | null;
  purchase_price?: number | null;
  salvage_value?: number | null;
  useful_life_months?: number | null;
  qty: number;
}

// Cermin cost_template_service.item_monthly_cost — untuk pratinjau di form saja;
// angka resmi (`monthly_cost`) tetap dari server. Null bila input belum lengkap.
export function itemMonthlyCost(item: ItemCostInput): number | null {
  if (item.item_type === "OVERHEAD") {
    if (item.monthly_amount == null) return null;
    return item.monthly_amount * item.qty;
  }
  if (item.purchase_price == null || !item.useful_life_months || item.useful_life_months <= 0)
    return null;
  return ((item.purchase_price - (item.salvage_value ?? 0)) / item.useful_life_months) * item.qty;
}
