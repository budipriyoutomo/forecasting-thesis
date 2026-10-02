import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { BomCostSummary } from "@/components/boms/BomCostSummary";
import type { Bom } from "@/types/bom";
import type { Product } from "@/types/product";

const products: Product[] = [
  { id: "p1", code: "KBYPL 200", name: "KIN Yogurt", category: null, unit: "PCS", cost_price: "4500" },
];

describe("BomCostSummary", () => {
  it("menampilkan total biaya material, HPP, dan selisih per produk", () => {
    const boms: Bom[] = [
      { id: "b1", product_id: "p1", material_id: "m1", qty_per_unit: "1", line_cost: "1500" },
      { id: "b2", product_id: "p1", material_id: "m2", qty_per_unit: "1", line_cost: "1000" },
    ];
    render(<BomCostSummary boms={boms} products={products} />);

    expect(screen.getByText("KBYPL 200 — KIN Yogurt")).toBeDefined();
    expect(screen.getByText("Rp 2.500")).toBeDefined();
    expect(screen.getByText("Rp 4.500")).toBeDefined();
    expect(screen.getByText("Rp 2.000")).toBeDefined();
  });

  it("memberi peringatan bila ada material tanpa harga", () => {
    const boms: Bom[] = [
      { id: "b1", product_id: "p1", material_id: "m1", qty_per_unit: "1", line_cost: "1500" },
      { id: "b2", product_id: "p1", material_id: "m2", qty_per_unit: "1", line_cost: null },
    ];
    render(<BomCostSummary boms={boms} products={products} />);

    expect(screen.getByText(/1 material belum punya harga/i)).toBeDefined();
  });

  it("tidak merender apa pun bila belum ada baris BOM", () => {
    const { container } = render(<BomCostSummary boms={[]} products={products} />);
    expect(container.textContent).toBe("");
  });
});
