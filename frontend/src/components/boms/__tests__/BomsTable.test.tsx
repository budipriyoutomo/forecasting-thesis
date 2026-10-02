import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { BomsTable } from "@/components/boms/BomsTable";
import type { Bom } from "@/types/bom";

describe("BomsTable", () => {
  it("menampilkan biaya per unit produk tiap baris (2 desimal), '—' bila tanpa harga", () => {
    const boms: Bom[] = [
      { id: "b1", product_id: "p1", material_id: "m1", qty_per_unit: "0.0125", line_cost: "181.25" },
      { id: "b2", product_id: "p1", material_id: "m2", qty_per_unit: "1", line_cost: null },
    ];
    render(<BomsTable boms={boms} products={[]} materials={[]} />);

    expect(screen.getByText("Rp 181,25")).toBeDefined();
    expect(screen.getByText("—")).toBeDefined();
  });
});
