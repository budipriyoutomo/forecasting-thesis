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

  it("kolom Level: baris komponen level 2 tampil di bawah material induknya, tanpa tombol Ubah", () => {
    const boms: Bom[] = [{ id: "b1", product_id: "p1", material_id: "btl", qty_per_unit: "1", level: 1 }];
    const components = [{ id: "c1", parent_material_id: "btl", component_material_id: "pre", qty_per_unit: 1 }];
    const materials = [
      { id: "btl", code: "BTL-WHITE", name: "Bottle White", unit: "PCS" },
      { id: "pre", code: "PRF-WHITE", name: "Preform White", unit: "PCS" },
    ] as never[];
    render(
      <BomsTable boms={boms} components={components} products={[]} materials={materials} onEdit={() => {}} />,
    );

    expect(screen.getByRole("columnheader", { name: /level/i })).toBeDefined();
    const cells = screen.getAllByRole("row").slice(1).map((r) => r.textContent ?? "");
    expect(cells[0]).toMatch(/BTL-WHITE/);
    expect(cells[1]).toMatch(/PRF-WHITE/);
    expect(cells[1]).toMatch(/BTL-WHITE/); // induk ditampilkan
    expect(screen.getAllByRole("button", { name: /ubah/i })).toHaveLength(1);
  });
});
