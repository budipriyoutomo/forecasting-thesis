import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StockSnapshotHistory } from "@/components/inventory/StockSnapshotHistory";
import { UsageHistoryTable } from "@/components/inventory/UsageHistoryTable";

// CR v3.5 §5.2 — riwayat dari GET /stock-snapshots & GET /material-usage (sebelumnya API-only).
describe("StockSnapshotHistory", () => {
  it("snapshot terbaru di atas, beserta satuan", () => {
    render(
      <StockSnapshotHistory
        snapshots={[
          { material_id: "m1", snapshot_date: "2026-09-01", qty: 900, uom: "PCS" },
          { material_id: "m1", snapshot_date: "2026-10-01", qty: 1200, uom: null },
        ]}
      />,
    );
    const rows = screen.getAllByRole("row").slice(1);
    expect(rows[0].textContent).toContain("1.200");
    expect(rows[1].textContent).toContain("900");
    expect(rows[1].textContent).toContain("PCS");
  });

  it("kosong → pesan belum ada snapshot", () => {
    render(<StockSnapshotHistory snapshots={[]} />);
    expect(screen.getByText(/belum ada snapshot/i)).toBeDefined();
  });
});

describe("UsageHistoryTable", () => {
  const PRODUCTS = [{ id: "p1", code: "SKU-1", name: "Teh" }] as never[];

  it("per periode: produk, output, standar, aktual, dan rasio aktual ÷ standar", () => {
    render(
      <UsageHistoryTable
        products={PRODUCTS}
        rows={[
          { material_id: "m1", product_id: "p1", period: "2026-10-01", production_output: 1000, standard_usage: 1000, actual_usage: 1030 },
          { material_id: "m1", product_id: null, period: "2026-09-01", production_output: null, standard_usage: 0, actual_usage: 5 },
        ]}
      />,
    );
    const rows = screen.getAllByRole("row").slice(1);
    expect(rows[0].textContent).toContain("SKU-1");
    expect(rows[0].textContent).toContain("1.030");
    expect(rows[0].textContent).toContain("103.0%");
    expect(rows[1].textContent).toContain("—"); // standar 0 → rasio tidak terdefinisi
  });

  it("kosong → pesan belum ada data", () => {
    render(<UsageHistoryTable rows={[]} products={[]} />);
    expect(screen.getByText(/belum ada data pemakaian/i)).toBeDefined();
  });
});
