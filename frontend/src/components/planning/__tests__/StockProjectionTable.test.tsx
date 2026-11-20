import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { StockProjectionTable } from "@/components/planning/StockProjectionTable";
import type { StockProjectionRow } from "@/types/planning";

const base = {
  material_id: "m1", receipt_qty: null, order_qty: 0, shortage_qty: 0, capacity_qty: 2000,
  utilization_opening_pct: 50, is_within_capacity: true,
};
const ROWS: StockProjectionRow[] = [
  { ...base, scenario: "proposed", period: "2026-11-01", opening_qty: 1200, usage_qty: 500,
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

  it("kedatangan = pesanan hasil ROP (satu kolom), tanpa kolom kedatangan manual", () => {
    render(<StockProjectionTable rows={ROWS} materials={MATERIALS} />);
    const headers = screen.getAllByRole("columnheader").map((h) => h.textContent);
    expect(headers).toContain("Kedatangan (ROP)");
    expect(headers).not.toContain("Kedatangan");
    expect(headers).not.toContain("Pesanan (EOQ)");
    expect(screen.getAllByRole("row")[2].textContent).toContain("2.000");
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

describe("StockProjectionTable — peringatan lead time (CR v3.5 §5.6)", () => {
  it("badge di judul material dengan lead time ≥ 30 hari", () => {
    render(<StockProjectionTable rows={ROWS} materials={[{ id: "m1", code: "BTL-WHITE", name: "Bottle White", unit: "PCS", lead_time_days: 30 }] as never[]} />);
    expect(screen.getByText(/lead time ≥ 1 periode/i)).toBeDefined();
  });

  it("lead time pendek → tanpa badge", () => {
    render(<StockProjectionTable rows={ROWS} materials={[{ id: "m1", code: "BTL-WHITE", name: "Bottle White", unit: "PCS", lead_time_days: 29 }] as never[]} />);
    expect(screen.queryByText(/lead time ≥ 1 periode/i)).toBeNull();
  });
});
