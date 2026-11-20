import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ExternalVariableValuesTable } from "@/components/external-variables/ExternalVariableValuesTable";

// CR v3.5 §5.2 — nilai per periode dari GET /external-variables/{id}/values.
describe("ExternalVariableValuesTable", () => {
  const PRODUCTS = [{ id: "p1", code: "SKU-1", name: "Teh" }] as never[];

  it("variabel per produk: kolom produk, periode terbaru dulu", () => {
    render(
      <ExternalVariableValuesTable
        scope="product"
        products={PRODUCTS}
        values={[
          { product_id: "p1", period: "2026-01-01", value: 1 },
          { product_id: "p1", period: "2026-02-01", value: 0 },
        ]}
      />,
    );
    expect(screen.getByRole("columnheader", { name: /produk/i })).toBeDefined();
    const rows = screen.getAllByRole("row").slice(1);
    expect(rows[0].textContent).toContain("SKU-1");
    expect(rows[0].textContent).toMatch(/Feb/);
  });

  it("variabel global: tanpa kolom produk", () => {
    render(<ExternalVariableValuesTable scope="global" products={[]} values={[{ product_id: null, period: "2026-01-01", value: 31.5 }]} />);
    expect(screen.queryByRole("columnheader", { name: /produk/i })).toBeNull();
    expect(screen.getByText("31,5")).toBeDefined();
  });

  it("kosong → arahkan ke import", () => {
    render(<ExternalVariableValuesTable scope="global" products={[]} values={[]} />);
    expect(screen.getByText(/belum ada nilai/i)).toBeDefined();
  });
});
