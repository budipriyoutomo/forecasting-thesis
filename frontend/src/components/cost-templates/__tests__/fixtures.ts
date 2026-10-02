import type { CostTemplate, CostTemplateSummary } from "@/types/costTemplate";

export const TEMPLATE: CostTemplate = {
  id: "t1",
  name: "Template 2026",
  description: null,
  ordering_cost: "250000.0000",
  holding_cost: "800.0000",
  is_active: true,
  items: [
    {
      id: "i1",
      item_type: "OVERHEAD",
      name: "Listrik",
      monthly_amount: "3000000.0000",
      purchase_price: null,
      salvage_value: null,
      useful_life_months: null,
      qty: "1.0000",
      monthly_cost: "3000000.0000",
    },
    {
      id: "i2",
      item_type: "STORAGE_ASSET",
      name: "Rak",
      monthly_amount: null,
      purchase_price: "50000000.0000",
      salvage_value: "5000000.0000",
      useful_life_months: 60,
      qty: "10.0000",
      monthly_cost: "7500000.0000",
    },
  ],
};

export const SUMMARY: CostTemplateSummary = {
  template_id: "t1",
  total_depreciation_monthly: "7500000.0000",
  total_overhead_monthly: "3000000.0000",
  total_monthly: "10500000.0000",
  total_capacity_dus: "20000.0000",
  suggested_holding_cost: "525.0000",
  holding_cost: "800.0000",
};
