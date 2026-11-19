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

  it("menampilkan kolom grup material ('—' bila belum dikelompokkan)", () => {
    const base = { name: "x", unit: "PCS", lead_time_days: 7, moq: "0", manual_safety_stock: null };
    const materials: Material[] = [
      { ...base, id: "m1", code: "CAP-RED", category: "cap" },
      { ...base, id: "m2", code: "LBL-1", category: null },
    ];
    render(<MaterialsTable materials={materials} />);

    expect(screen.getByRole("columnheader", { name: /grup/i })).toBeDefined();
    expect(screen.getByText("cap")).toBeDefined();
  });
});
