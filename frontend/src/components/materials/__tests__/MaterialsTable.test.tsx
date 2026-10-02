import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MaterialsTable } from "@/components/materials/MaterialsTable";
import type { Material } from "@/types/material";

describe("MaterialsTable", () => {
  it("menampilkan harga beli per unit dalam Rupiah", () => {
    const materials: Material[] = [
      {
        id: "m1",
        code: "RM-1",
        name: "Gula",
        category: null,
        unit: "kg",
        lead_time_days: 5,
        moq: "50",
        manual_safety_stock: null,
        unit_price: "14500",
      },
    ];
    render(<MaterialsTable materials={materials} />);

    expect(screen.getByText("Rp 14.500")).toBeDefined();
  });
});
