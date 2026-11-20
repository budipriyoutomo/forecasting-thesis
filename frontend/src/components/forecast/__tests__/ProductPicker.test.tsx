import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ProductPicker } from "@/components/forecast/ProductPicker";
import type { Product } from "@/types/product";

const P = (id: string, code: string, name: string): Product => ({ id, code, name, category: null, unit: "BTL" });
const PRODUCTS = [P("p1", "TEH-1", "Teh Melati"), P("p2", "TEH-2", "Teh Hijau"), P("p3", "KOP-1", "Kopi Susu")];
const COVERAGE = [
  { product_id: "p1", n_periods: 24, last_period: "2026-10-01" },
  { product_id: "p2", n_periods: 8, last_period: "2026-10-01" },
  { product_id: "p3", n_periods: 0, last_period: null },
];

describe("ProductPicker (CR v3.6 §5)", () => {
  it("menampilkan jumlah bulan histori & tanda bila kurang dari minimal", () => {
    render(<ProductPicker products={PRODUCTS} coverage={COVERAGE} selected={[]} onChange={vi.fn()} />);
    expect(screen.getByText("24 bulan")).toBeDefined();
    expect(screen.getByText("8 bulan")).toBeDefined();
    expect(screen.getAllByText("kurang dari 12")).toHaveLength(2); // 8 & 0
  });

  it("search lalu 'pilih semua hasil filter' hanya memilih produk yang tersaring", async () => {
    const onChange = vi.fn();
    render(<ProductPicker products={PRODUCTS} coverage={COVERAGE} selected={["p3"]} onChange={onChange} />);

    await userEvent.type(screen.getByRole("searchbox", { name: /cari produk/i }), "teh");
    expect(screen.queryByText("KOP-1")).toBeNull();
    await userEvent.click(screen.getByRole("checkbox", { name: /pilih semua hasil filter/i }));

    expect(onChange).toHaveBeenCalledWith(["p3", "p1", "p2"]);
  });

  it("centang satu produk", async () => {
    const onChange = vi.fn();
    render(<ProductPicker products={PRODUCTS} selected={[]} onChange={onChange} />);
    await userEvent.click(screen.getByRole("checkbox", { name: "Pilih TEH-2" }));
    expect(onChange).toHaveBeenCalledWith(["p2"]);
  });
});
