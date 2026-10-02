import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ProductsTable } from "@/components/products/ProductsTable";
import type { Product } from "@/types/product";

describe("ProductsTable", () => {
  it("menampilkan HPP & harga jual dalam Rupiah, '—' bila kosong", () => {
    const products: Product[] = [
      { id: "p1", code: "A", name: "Produk A", category: null, unit: "PCS", cost_price: "4500", selling_price: "6000" },
      { id: "p2", code: "B", name: "Produk B", category: null, unit: "PCS", cost_price: null, selling_price: null },
    ];
    render(<ProductsTable products={products} />);

    expect(screen.getByText("Rp 4.500")).toBeDefined();
    expect(screen.getByText("Rp 6.000")).toBeDefined();
    expect(screen.getAllByText("—").length).toBeGreaterThanOrEqual(2);
  });
});
