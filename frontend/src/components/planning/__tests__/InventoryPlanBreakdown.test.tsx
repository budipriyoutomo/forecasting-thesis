import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { InventoryPlanBreakdown } from "@/components/planning/InventoryPlanBreakdown";
import type { StockProjectionRow } from "@/types/planning";
import type { ReorderRecommendation } from "@/types/reorder";

const row = (over: Partial<StockProjectionRow>): StockProjectionRow => ({
  material_id: "m1", scenario: "proposed", period: "2026-11-01", opening_qty: 0, receipt_qty: null,
  usage_qty: 0, order_qty: 0, ending_qty: 0, shortage_qty: 0, capacity_qty: 10000,
  utilization_opening_pct: null, utilization_ending_pct: null, is_within_capacity: null, ...over,
});

// m1 & m2 satu grup "Cap" (kapasitas 10.000) — utilisasi grup dari backend; m3 tanpa grup.
const PROJECTION: StockProjectionRow[] = [
  row({ material_id: "m1", period: "2026-11-01", opening_qty: 1000, usage_qty: 600, order_qty: 0, ending_qty: 400,
    utilization_opening_pct: 15, utilization_ending_pct: 6, is_within_capacity: true }),
  row({ material_id: "m1", period: "2026-12-01", opening_qty: 400, usage_qty: 900, order_qty: 5000, ending_qty: 4500,
    utilization_opening_pct: 6, utilization_ending_pct: 120, is_within_capacity: false }),
  row({ material_id: "m2", period: "2026-11-01", opening_qty: 500, usage_qty: 100, order_qty: 0, ending_qty: 400,
    utilization_opening_pct: 15, utilization_ending_pct: 6, is_within_capacity: true }),
  row({ material_id: "m2", period: "2026-12-01", opening_qty: 400, usage_qty: 100, order_qty: 7300, ending_qty: 7600,
    utilization_opening_pct: 6, utilization_ending_pct: 120, is_within_capacity: false }),
  row({ material_id: "m3", period: "2026-11-01", opening_qty: 0, usage_qty: 50, ending_qty: 0, shortage_qty: 50, capacity_qty: null }),
  row({ material_id: "m3", period: "2026-12-01", opening_qty: 0, usage_qty: 50, ending_qty: 0, shortage_qty: 50, capacity_qty: null }),
  row({ material_id: "m1", scenario: "baseline", period: "2026-11-01", opening_qty: 1000, usage_qty: 700, ending_qty: 300 }),
];

const rec = (over: Partial<ReorderRecommendation>): ReorderRecommendation => ({
  material_id: "m1", safety_stock: "120.5", reorder_point: "500", recommended_order_qty: "5000", status: "urgent",
  buffer_stock: "30", waste_factor: "1.04", eoq_qty: "5000", eoq_raw_qty: "4472.136", eoq_method: "classic",
  item_status: "COMPLETED", annual_demand: "9000", unit_price_used: "1500", holding_rate_used: "20",
  ordering_cost_per_order: "250000", holding_cost_per_unit: "10", moq_used: "5000",
  rop_formula_used: "with_buffer", order_qty_policy_used: "eoq", order_up_to_level: "740",
  current_stock_used: "1000", stock_source: "snapshot", mu_period: "750", sigma_period: "212.13",
  period_days: "30", lead_time_days_used: "7", z_value: "1.6449", service_level_pct_used: "95",
  ordering_cost: "450000", holding_cost: "750000", total_inventory_cost: "1200000", ...over,
});

const RECS = [rec({}), rec({ material_id: "m2", safety_stock: "10", buffer_stock: "0", waste_factor: null, eoq_method: "dynamic",
  eoq_qty: "7300", eoq_raw_qty: "7300", moq_used: "0", holding_rate_used: null, mu_period: "100" })];

const MATERIALS = [
  { id: "m1", code: "CAP-01", name: "Cap Merah", unit: "PCS", category: "Cap", lead_time_days: 7, manual_safety_stock: null },
  { id: "m2", code: "CAP-02", name: "Cap Biru", unit: "PCS", category: "cap", lead_time_days: 7, manual_safety_stock: null },
  { id: "m3", code: "LBL-01", name: "Label", unit: "PCS", category: null, lead_time_days: 7, manual_safety_stock: null },
] as never[];

const renderIt = () =>
  render(<InventoryPlanBreakdown projection={PROJECTION} recommendations={RECS} materials={MATERIALS} />);

const rowOf = (name: string) => screen.getAllByRole("row").find((r) => r.textContent?.includes(name)) as HTMLElement;

describe("InventoryPlanBreakdown — Perencanaan persediaan", () => {
  it("1. MRP per bulan per material (forecast × BOM), dengan total horizon", () => {
    renderIt();
    const headers = screen.getAllByRole("columnheader").map((h) => h.textContent);
    expect(headers).toEqual(expect.arrayContaining(["Material", "Total"]));
    expect(headers.filter((h) => /2026/.test(h ?? ""))).toHaveLength(2);
    const m1 = rowOf("CAP-01");
    expect(m1.textContent).toContain("600");
    expect(m1.textContent).toContain("900");
    expect(m1.textContent).toContain("1.500"); // total = 600 + 900, skenario usulan saja
  });

  it("2. safety stock & buffer stock beserta input perhitungannya", async () => {
    renderIt();
    await userEvent.click(screen.getByRole("tab", { name: /safety/i }));
    const m1 = rowOf("CAP-01");
    expect(m1.textContent).toContain("1,6449"); // Z
    expect(m1.textContent).toContain("95%");
    expect(m1.textContent).toContain("120,5"); // SS
    expect(m1.textContent).toContain("1,04"); // faktor waste
    expect(m1.textContent).toContain("30"); // buffer
    expect(rowOf("CAP-02").textContent).toMatch(/belum ada data pemakaian/i);
  });

  it("3. total kebutuhan = MRP + safety stock + buffer stock", async () => {
    renderIt();
    await userEvent.click(screen.getByRole("tab", { name: /total kebutuhan/i }));
    // 1.500 + 120,5 + 30
    expect(rowOf("CAP-01").textContent).toContain("1.650,5");
  });

  it("4. EOQ dari kebutuhan & MOQ, plus kebijakan inventory", async () => {
    renderIt();
    await userEvent.click(screen.getByRole("tab", { name: /eoq/i }));
    const m1 = rowOf("CAP-01");
    expect(m1.textContent).toContain("4.472,14"); // EOQ hitung
    expect(m1.textContent).toContain("5.000"); // MOQ & EOQ dipakai
    expect(m1.textContent).toMatch(/klasik/i);
    expect(rowOf("CAP-02").textContent).toMatch(/dinamis/i);
    expect(screen.getAllByText(/kelipatan EOQ/i).length).toBeGreaterThan(0);
  });

  it("5. ROP = μ harian × L + SS + buffer, dengan jadwal pesan dari proyeksi", async () => {
    renderIt();
    await userEvent.click(screen.getByRole("tab", { name: /rop/i }));
    const m1 = rowOf("CAP-01");
    expect(m1.textContent).toContain("25"); // μ harian = 750 ÷ 30
    expect(m1.textContent).toContain("175"); // μ·L = 25 × 7
    expect(m1.textContent).toContain("500"); // ROP tersimpan
    expect(m1.textContent).toMatch(/1 Des 2026/); // periode pesan pertama
  });

  it("6. kapasitas & utilisasi gudang per grup material (kedatangan ROP, qty EOQ)", async () => {
    renderIt();
    await userEvent.click(screen.getByRole("tab", { name: /kapasitas/i }));
    const section = screen.getByRole("region", { name: /grup cap/i });
    const rows = within(section).getAllByRole("row").slice(1);
    expect(rows).toHaveLength(2);
    expect(rows[1].textContent).toContain("12.300"); // kedatangan 5.000 + 7.300
    expect(rows[1].textContent).toContain("12.100"); // stok akhir 4.500 + 7.600
    expect(rows[1].textContent).toContain("120.0%");
    expect(rows[1].textContent).toMatch(/melebihi/i);
    expect(screen.getByText(/LBL-01/)).toBeDefined(); // material tanpa grup disebut
  });

  it("6. peringatan bila qty pembelian bukan EOQ (kebijakan order-up-to)", async () => {
    render(
      <InventoryPlanBreakdown
        projection={PROJECTION}
        recommendations={RECS.map((r) => ({ ...r, order_qty_policy_used: "order_up_to" as const }))}
        materials={MATERIALS}
      />,
    );
    await userEvent.click(screen.getByRole("tab", { name: /kapasitas/i }));
    expect(screen.getByText(/Pengaturan Forecast/i)).toBeDefined();
  });

  it("7. simulasi stok in/out tanpa kolom utilisasi gudang", async () => {
    renderIt();
    await userEvent.click(screen.getByRole("tab", { name: /simulasi/i }));
    const headers = screen.getAllByRole("columnheader").map((h) => h.textContent ?? "");
    expect(headers).toEqual(expect.arrayContaining(["Stok awal", "Masuk (kedatangan)", "Keluar (pemakaian)", "Stok akhir"]));
    expect(headers.some((h) => /utilisasi/i.test(h))).toBe(false);
  });

  it("rekomendasi lama tanpa input perhitungan tampil — dan minta jalankan ulang", async () => {
    render(
      <InventoryPlanBreakdown
        projection={PROJECTION}
        recommendations={[rec({ mu_period: null, sigma_period: null, z_value: null, period_days: null })]}
        materials={MATERIALS}
      />,
    );
    await userEvent.click(screen.getByRole("tab", { name: /safety/i }));
    expect(screen.getByText(/jalankan ulang perencanaan/i)).toBeDefined();
  });
});
