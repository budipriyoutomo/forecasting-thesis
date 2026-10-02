import { describe, expect, it } from "vitest";

import { summarizeBomCosts } from "@/lib/bom";
import type { Bom } from "@/types/bom";
import type { Product } from "@/types/product";

const products: Product[] = [
  { id: "p1", code: "A", name: "Produk A", category: null, unit: "PCS", cost_price: "4500" },
  { id: "p2", code: "B", name: "Produk B", category: null, unit: "PCS", cost_price: null },
];

const bom = (id: string, product_id: string, line_cost: string | null): Bom => ({
  id,
  product_id,
  material_id: `m-${id}`,
  qty_per_unit: "1",
  line_cost,
});

describe("summarizeBomCosts", () => {
  it("menjumlah biaya material per produk & menghitung selisih terhadap HPP", () => {
    const [a] = summarizeBomCosts([bom("1", "p1", "181.25"), bom("2", "p1", "1200")], products);
    expect(a.product_id).toBe("p1");
    expect(a.material_cost).toBeCloseTo(1381.25);
    expect(a.cost_price).toBe(4500);
    expect(a.margin_vs_hpp).toBeCloseTo(3118.75); // 4500 − 1381,25
    expect(a.n_without_price).toBe(0);
  });

  it("material tanpa harga dihitung terpisah, total hanya dari yang berharga", () => {
    const [a] = summarizeBomCosts([bom("1", "p1", "100"), bom("2", "p1", null)], products);
    expect(a.material_cost).toBe(100);
    expect(a.n_without_price).toBe(1);
  });

  it("produk tanpa HPP → selisih null; urut sesuai kode produk", () => {
    const rows = summarizeBomCosts([bom("1", "p2", "50"), bom("2", "p1", "10")], products);
    expect(rows.map((r) => r.product_id)).toEqual(["p1", "p2"]);
    expect(rows[1].cost_price).toBeNull();
    expect(rows[1].margin_vs_hpp).toBeNull();
  });
});
