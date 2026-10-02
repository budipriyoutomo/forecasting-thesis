import { describe, expect, it } from "vitest";

import { itemMonthlyCost } from "@/lib/costTemplate";

// Cermin cost_template_service.item_monthly_cost (backend) — angka manual sama.
describe("itemMonthlyCost", () => {
  it("overhead = biaya per bulan × qty", () => {
    expect(itemMonthlyCost({ item_type: "OVERHEAD", monthly_amount: 3_000_000, qty: 2 })).toBe(6_000_000);
  });

  it("aset = (harga beli − nilai sisa) ÷ umur bulan × qty", () => {
    expect(
      itemMonthlyCost({
        item_type: "STORAGE_ASSET",
        purchase_price: 50_000_000,
        salvage_value: 5_000_000,
        useful_life_months: 60,
        qty: 10,
      }),
    ).toBe(7_500_000);
  });

  it("null bila input belum lengkap", () => {
    expect(itemMonthlyCost({ item_type: "STORAGE_ASSET", purchase_price: 1000, qty: 1 })).toBeNull();
    expect(itemMonthlyCost({ item_type: "OVERHEAD", qty: 1 })).toBeNull();
  });
});
