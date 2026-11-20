import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LatestStockTable } from "@/components/inventory/LatestStockTable";
import { WasteFactorTable } from "@/components/inventory/WasteFactorTable";

const MATERIALS = [
  { id: "m1", code: "CAP-WHITE", name: "Cap White", unit: "PCS" },
  { id: "m2", code: "BTL-WHITE", name: "Bottle White", unit: "PCS" },
] as never[];

describe("Persediaan material (Fase 11.1/11.5)", () => {
  it("stok ERP terakhir per material + material tanpa snapshot", () => {
    render(<LatestStockTable latest={[{ material_id: "m1", snapshot_date: "2026-10-01", qty: 1200 }]} materials={MATERIALS} />);
    expect(screen.getByText("CAP-WHITE")).toBeDefined();
    expect(screen.getByText("1.200")).toBeDefined();
    expect(screen.getByText(/belum ada snapshot/i)).toBeDefined(); // BTL-WHITE
  });

  it("faktor waste & persentase buffer", () => {
    render(<WasteFactorTable factors={[{ material_id: "m1", waste_factor: 1.03 }, { material_id: "m2", waste_factor: null }]} materials={MATERIALS} />);
    expect(screen.getByText("1.030")).toBeDefined();
    expect(screen.getByText("+3.0%")).toBeDefined();
    expect(screen.getByText(/standar 0/i)).toBeDefined();
  });
});
