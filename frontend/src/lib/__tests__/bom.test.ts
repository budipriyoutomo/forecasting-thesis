import { describe, expect, it } from "vitest";

import { flattenBomLevels, summarizeBomCosts } from "@/lib/bom";
import type { Bom } from "@/types/bom";
import type { Product } from "@/types/product";

const products: Product[] = [
  { id: "p1", code: "A", name: "Produk A", category: null, unit: "PCS", selling_price: "4500" },
  { id: "p2", code: "B", name: "Produk B", category: null, unit: "PCS", selling_price: null },
];

const bom = (id: string, product_id: string, line_cost: string | null): Bom => ({
  id,
  product_id,
  material_id: `m-${id}`,
  qty_per_unit: "1",
  line_cost,
});

describe("summarizeBomCosts", () => {
  it("menjumlah biaya material per produk & menghitung selisih terhadap harga produk", () => {
    const [a] = summarizeBomCosts([bom("1", "p1", "181.25"), bom("2", "p1", "1200")], products);
    expect(a.product_id).toBe("p1");
    expect(a.material_cost).toBeCloseTo(1381.25);
    expect(a.product_price).toBe(4500);
    expect(a.margin).toBeCloseTo(3118.75); // 4500 − 1381,25
    expect(a.n_without_price).toBe(0);
  });

  it("material tanpa harga dihitung terpisah, total hanya dari yang berharga", () => {
    const [a] = summarizeBomCosts([bom("1", "p1", "100"), bom("2", "p1", null)], products);
    expect(a.material_cost).toBe(100);
    expect(a.n_without_price).toBe(1);
  });

  it("produk tanpa harga → selisih null; urut sesuai kode produk", () => {
    const rows = summarizeBomCosts([bom("1", "p2", "50"), bom("2", "p1", "10")], products);
    expect(rows.map((r) => r.product_id)).toEqual(["p1", "p2"]);
    expect(rows[1].product_price).toBeNull();
    expect(rows[1].margin).toBeNull();
  });
});

describe("flattenBomLevels", () => {
  const boms = [
    { id: "b1", product_id: "p1", material_id: "btl", qty_per_unit: "1" },
    { id: "b2", product_id: "p1", material_id: "cap", qty_per_unit: "1" },
  ];
  const components = [
    { id: "c1", parent_material_id: "btl", component_material_id: "pre", qty_per_unit: 1 },
    { id: "c2", parent_material_id: "pre", component_material_id: "resin", qty_per_unit: 0.02 },
  ];

  it("level 1 dari BOM, level 2+ dari komponen, urut di bawah induknya", () => {
    const rows = flattenBomLevels(boms, components);
    expect(rows.map((r) => [r.level, r.material_id, r.parent_material_id])).toEqual([
      [1, "btl", null],
      [2, "pre", "btl"],
      [3, "resin", "pre"],
      [1, "cap", null],
    ]);
    expect(rows.every((r) => r.product_id === "p1")).toBe(true);
    expect(rows[0].bom?.id).toBe("b1");
    expect(rows[1].component_id).toBe("c1");
  });

  it("data siklus tidak membuat loop tak berujung", () => {
    const cyc = [
      { id: "c1", parent_material_id: "btl", component_material_id: "pre", qty_per_unit: 1 },
      { id: "c2", parent_material_id: "pre", component_material_id: "btl", qty_per_unit: 1 },
    ];
    expect(flattenBomLevels([boms[0]], cyc).map((r) => r.material_id)).toEqual(["btl", "pre"]);
  });
});
