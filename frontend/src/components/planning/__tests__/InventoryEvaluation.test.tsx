import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { InventoryEvaluation } from "@/components/planning/InventoryEvaluation";
import type { CostSummary, InventoryMetric } from "@/types/metrics";
import type { ReorderRecommendation } from "@/types/reorder";

const metric = (over: Partial<InventoryMetric>): InventoryMetric => ({
  target_type: "material", target_id: "m1", scope: "forecastiq", service_level: "1", fill_rate: "1",
  stock_out_rate: "0", inventory_turnover: "4", inventory_days: "7.5", shortage_cost: "0", ...over,
});

// Rata-rata material: β existing (0,8 + 0,9)/2 = 0,85 → usulan (1 + 0,96)/2 = 0,98
const METRICS: InventoryMetric[] = [
  metric({ scope: "baseline", fill_rate: "0.8", service_level: "0.75", stock_out_rate: "0.25", inventory_turnover: "2", shortage_cost: "500000" }),
  metric({ scope: "baseline", target_id: "m2", fill_rate: "0.9", service_level: "0.75", stock_out_rate: "0.25", inventory_turnover: "3", shortage_cost: "100000" }),
  metric({ target_id: "m1", fill_rate: "1", stock_out_rate: "0", inventory_turnover: "4" }),
  metric({ target_id: "m2", fill_rate: "0.96", service_level: "0.75", stock_out_rate: "0.25", inventory_turnover: "5", shortage_cost: "20000" }),
  metric({ target_type: "product", target_id: "p1", fill_rate: "0.5" }), // level produk tidak ikut rata-rata material
];

const COST: CostSummary = {
  run_id: "r1", total_ordering_cost: "900000", total_holding_cost: "300000", total_inventory_cost: "1200000",
  baseline_inventory_cost: "2000000", baseline_ordering_cost: "1500000", baseline_holding_cost: "500000",
  savings_pct: "40", shortage_cost: "20000", baseline_shortage_cost: "600000",
};

const RECS = [
  { material_id: "m1", ordering_cost: "500000", holding_cost: "200000", total_inventory_cost: "700000" },
  { material_id: "m2", ordering_cost: "400000", holding_cost: "100000", total_inventory_cost: "500000" },
] as ReorderRecommendation[];

const MATERIALS = [
  { id: "m1", code: "CAP-01", name: "Cap", unit: "PCS" },
  { id: "m2", code: "BTL-01", name: "Botol", unit: "PCS" },
] as never[];
const PRODUCTS = [{ id: "p1", code: "SKU-1", name: "Teh" }] as never[];

const renderIt = (cost: CostSummary | null = COST) =>
  render(<InventoryEvaluation metrics={METRICS} cost={cost} recommendations={RECS} materials={MATERIALS} products={PRODUCTS} />);

const rowOf = (re: RegExp) => screen.getAllByRole("row").find((r) => re.test(r.textContent ?? "")) as HTMLElement;

describe("InventoryEvaluation — evaluasi usulan inventory", () => {
  it("fulfilment rate (service level): existing vs usulan, rata-rata material", () => {
    renderIt();
    const row = rowOf(/fulfilment rate/i);
    expect(row.textContent).toContain("85%");
    expect(row.textContent).toContain("98%");
    expect(row.textContent).toMatch(/\+13 pp/);
    expect(row.textContent).toMatch(/lebih baik/i);
  });

  it("stockout rate & inventory turnover", () => {
    renderIt();
    const so = rowOf(/^stockout rate/i);
    expect(so.textContent).toContain("25%");
    expect(so.textContent).toContain("12,5%");
    expect(so.textContent).toMatch(/lebih baik/i); // turun = lebih baik
    const to = rowOf(/inventory turnover/i);
    expect(to.textContent).toContain("2,5×");
    expect(to.textContent).toContain("4,5×");
  });

  it("holding cost, ordering cost, shortage cost & TIC existing vs usulan", () => {
    renderIt();
    expect(rowOf(/ordering cost/i).textContent).toMatch(/Rp 1\.500\.000.*Rp 900\.000/);
    expect(rowOf(/holding cost/i).textContent).toMatch(/Rp 500\.000.*Rp 300\.000/);
    expect(rowOf(/shortage cost/i).textContent).toMatch(/Rp 600\.000.*Rp 20\.000/);
    expect(rowOf(/total biaya persediaan/i).textContent).toMatch(/40%/);
  });

  it("rincian per material: metrik kedua skenario + biaya pesan/simpan usulan", () => {
    renderIt();
    const m1 = rowOf(/CAP-01/);
    expect(m1.textContent).toContain("80%");
    expect(m1.textContent).toContain("100%");
    expect(m1.textContent).toContain("Rp 500.000");
    expect(m1.textContent).toContain("Rp 200.000");
  });

  it("biaya belum tersedia → tampil — tanpa error", () => {
    renderIt(null);
    expect(rowOf(/ordering cost/i).textContent).toContain("—");
  });

  it("belum ada metrik → empty state", () => {
    render(<InventoryEvaluation metrics={[]} recommendations={[]} materials={[]} products={[]} />);
    expect(screen.getByText(/belum ada metrik/i)).toBeDefined();
  });
});
