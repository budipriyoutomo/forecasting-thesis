import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { StockProjectionTable } from "@/components/planning/StockProjectionTable";
import type { StockProjectionRow } from "@/types/planning";

const base = {
  material_id: "m1", receipt_qty: 0, order_qty: 0, shortage_qty: 0, capacity_qty: 2000,
  utilization_opening_pct: 50, is_within_capacity: true,
};
const ROWS: StockProjectionRow[] = [
  { ...base, scenario: "proposed", period: "2026-11-01", opening_qty: 1000, usage_qty: 500, receipt_qty: 200,
    ending_qty: 700, utilization_ending_pct: 35 },
  { ...base, scenario: "proposed", period: "2026-12-01", opening_qty: 700, usage_qty: 400, ending_qty: 2300,
    order_qty: 2000, utilization_opening_pct: 35, utilization_ending_pct: 115, is_within_capacity: false },
  { ...base, scenario: "baseline", period: "2026-11-01", opening_qty: 1000, usage_qty: 900, ending_qty: 300,
    utilization_ending_pct: 15 },
];
const MATERIALS = [{ id: "m1", code: "BTL-WHITE", name: "Bottle White", unit: "PCS" }] as never[];

describe("StockProjectionTable", () => {
  it("menampilkan stok awal, kedatangan, pemakaian, pesanan, stok akhir & utilisasi per periode", () => {
    render(<StockProjectionTable rows={ROWS} materials={MATERIALS} />);

    expect(screen.getByText("BTL-WHITE — Bottle White")).toBeDefined();
    const rows = screen.getAllByRole("row").slice(1);
    expect(rows).toHaveLength(2); // default skenario usulan
    expect(rows[0].textContent).toContain("35.0%");
    expect(rows[1].textContent).toMatch(/melebihi/i);
    expect(rows[1].textContent).toContain("115.0%");
  });

  it("beralih ke skenario baseline (planning)", async () => {
    render(<StockProjectionTable rows={ROWS} materials={MATERIALS} />);
    await userEvent.click(screen.getByRole("tab", { name: /planning/i }));

    const rows = screen.getAllByRole("row").slice(1);
    expect(rows).toHaveLength(1);
    expect(rows[0].textContent).toContain("15.0%");
  });

  it("tab baseline nonaktif bila tidak ada data planning horizon", () => {
    render(<StockProjectionTable rows={ROWS.filter((r) => r.scenario === "proposed")} materials={MATERIALS} />);
    expect((screen.getByRole("tab", { name: /planning/i }) as HTMLButtonElement).disabled).toBe(true);
  });
});
