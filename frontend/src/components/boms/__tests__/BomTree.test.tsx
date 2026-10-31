import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { BomTree } from "@/components/boms/BomTree";

describe("BomTree (Fase 11.3)", () => {
  it("menampilkan FG → material → komponen dengan penanda dibeli/informasi", () => {
    render(
      <BomTree
        tree={{
          product_id: "p1", code: "KBYPL 200", name: "Original", level: 0,
          children: [
            { material_id: "btl", code: "BTL-WHITE", name: "Bottle White", unit: "PCS", qty_per_unit: 1, level: 1,
              purchased: true, component_id: null,
              children: [{ material_id: "pre", code: "PRE-WHITE", name: "Preform White", unit: "PCS",
                           qty_per_unit: 1, level: 2, purchased: false, component_id: "c1", children: [] }] },
          ],
        }}
      />,
    );
    const items = screen.getAllByRole("treeitem");
    expect(items).toHaveLength(3);
    expect(items[0].getAttribute("aria-level")).toBe("1");
    expect(screen.getByText(/BTL-WHITE/).closest("[role=treeitem]")?.getAttribute("aria-level")).toBe("2");
    expect(screen.getByText(/dibeli/i)).toBeDefined();
    expect(screen.getByText(/informasi/i)).toBeDefined();
  });
});
