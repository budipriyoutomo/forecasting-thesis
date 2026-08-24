import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { WarehouseCapacityBadge } from "@/components/warehouse/WarehouseCapacityBadge";
import type { WarehouseValidation } from "@/types/warehouse";
import type { Product } from "@/types/product";

const products: Product[] = [
  { id: "p1", code: "KBYPL 200", name: "KIN Yogurt 200ml", category: null, unit: "PCS" },
  { id: "p2", code: "KBYST 200", name: "KIN Yogurt Strawberry 200ml", category: null, unit: "PCS" },
];

describe("WarehouseCapacityBadge", () => {
  it("menampilkan status muat saat semua produk dalam kapasitas", () => {
    const validation: WarehouseValidation = {
      run_id: "r1",
      is_within_capacity: true,
      details: [
        { product_id: "p1", required_qty: "80", capacity_qty: "100", is_within_capacity: true },
      ],
    };
    render(<WarehouseCapacityBadge validation={validation} products={products} />);

    expect(screen.getByText(/muat di gudang/i)).toBeDefined();
    expect(screen.getByText("KBYPL 200 — KIN Yogurt 200ml")).toBeDefined();
  });

  it("menandai produk yang melebihi kapasitas secara individual", () => {
    const validation: WarehouseValidation = {
      run_id: "r1",
      is_within_capacity: false,
      details: [
        { product_id: "p1", required_qty: "80", capacity_qty: "100", is_within_capacity: true },
        { product_id: "p2", required_qty: "120", capacity_qty: "100", is_within_capacity: false },
      ],
    };
    render(<WarehouseCapacityBadge validation={validation} products={products} />);

    expect(screen.getByText(/melebihi kapasitas gudang/i)).toBeDefined();
    expect(screen.getAllByText(/melebihi/i).length).toBeGreaterThan(0);
  });

  it("menampilkan pesan saat tidak ada produk yang bisa dibandingkan", () => {
    const validation: WarehouseValidation = { run_id: "r1", is_within_capacity: true, details: [] };
    render(<WarehouseCapacityBadge validation={validation} products={products} />);

    expect(screen.getByText(/belum ada produk yang bisa dibandingkan/i)).toBeDefined();
  });
});
