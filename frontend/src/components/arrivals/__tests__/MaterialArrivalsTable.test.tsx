import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MaterialArrivalsTable } from "@/components/arrivals/MaterialArrivalsTable";
import type { StockProjectionRow } from "@/types/planning";
import type { ReorderRecommendation } from "@/types/reorder";

const base = {
  receipt_qty: null, shortage_qty: 0, capacity_qty: null, utilization_opening_pct: null,
  utilization_ending_pct: null, is_within_capacity: null,
};
const ROWS: StockProjectionRow[] = [
  { ...base, material_id: "m1", scenario: "proposed", period: "2026-11-01", opening_qty: 1000, usage_qty: 300,
    order_qty: 0, ending_qty: 700 },
  { ...base, material_id: "m1", scenario: "proposed", period: "2026-12-01", opening_qty: 700, usage_qty: 500,
    order_qty: 900, ending_qty: 1100 },
  { ...base, material_id: "m2", scenario: "proposed", period: "2026-11-01", opening_qty: 50, usage_qty: 40,
    order_qty: 300, ending_qty: 310 },
  // skenario existing (planning) bukan kedatangan usulan sistem
  { ...base, material_id: "m1", scenario: "baseline", period: "2026-11-01", opening_qty: 1000, usage_qty: 900,
    order_qty: 777, ending_qty: 877 },
];
const RECS = [
  { material_id: "m1", reorder_point: "400", order_qty_policy_used: "order_up_to", status: "safe" },
  { material_id: "m2", reorder_point: "60", order_qty_policy_used: "eoq", status: "urgent" },
] as ReorderRecommendation[];
const MATERIALS = [
  { id: "m1", code: "BTL-WHITE", name: "Bottle White", unit: "PCS" },
  { id: "m2", code: "CAP-RED", name: "Cap Red", unit: "PCS" },
] as never[];

describe("MaterialArrivalsTable — kedatangan hasil hitungan ROP", () => {
  it("hanya periode yang memesan (skenario usulan), urut periode lalu material", () => {
    render(<MaterialArrivalsTable rows={ROWS} recommendations={RECS} materials={MATERIALS} />);
    const rows = screen.getAllByRole("row").slice(1);
    expect(rows).toHaveLength(2);
    expect(rows[0].textContent).toContain("CAP-RED");
    expect(rows[1].textContent).toContain("BTL-WHITE");
    expect(screen.queryByText("777")).toBeNull();
  });

  it("menampilkan stok sebelum pesan, ROP, qty tiba & kebijakan", () => {
    render(<MaterialArrivalsTable rows={ROWS} recommendations={RECS} materials={MATERIALS} />);
    const row = screen.getAllByRole("row")[2]; // BTL-WHITE Des 2026
    expect(row.textContent).toContain("200"); // 700 − 500
    expect(row.textContent).toContain("400"); // ROP
    expect(row.textContent).toContain("900"); // qty tiba
    expect(row.textContent).toMatch(/order-up-to/i);
    expect(screen.getAllByRole("row")[1].textContent).toMatch(/n × EOQ/);
  });

  it("total qty tiba per material", () => {
    render(<MaterialArrivalsTable rows={ROWS} recommendations={RECS} materials={MATERIALS} />);
    expect(screen.getByText(/2 kedatangan/i)).toBeDefined();
  });

  it("pesan kosong bila tidak ada kedatangan", () => {
    render(<MaterialArrivalsTable rows={ROWS.slice(0, 1)} recommendations={RECS} materials={MATERIALS} />);
    expect(screen.getByText(/tidak ada kedatangan/i)).toBeDefined();
  });
});
