import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { BomForm } from "@/components/boms/BomForm";
import type { Material } from "@/types/material";
import type { Product } from "@/types/product";

const PRODUCTS: Product[] = [
  { id: "p1", code: "KBYPL 200", name: "KIN Yogurt 200ml", category: null, unit: "PCS" },
];
const MATERIALS: Material[] = [
  {
    id: "m1",
    code: "BTL-200",
    name: "Botol 200ml",
    category: null,
    unit: "pcs",
    lead_time_days: 7,
    moq: "1000",
    manual_safety_stock: null,
  },
];

afterEach(() => vi.restoreAllMocks());

describe("BomForm", () => {
  it("validasi produk/material wajib dipilih", async () => {
    const onSubmit = vi.fn();
    render(<BomForm products={PRODUCTS} materials={MATERIALS} onSubmit={onSubmit} />);

    await userEvent.click(screen.getByRole("button", { name: /simpan/i }));

    expect(await screen.findByText(/Produk wajib dipilih/i)).toBeDefined();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  // Produk & material sekarang memakai Radix Select, bukan <select> native — jadi
  // pemilihannya lewat klik trigger lalu klik option, bukan userEvent.selectOptions.
  async function pilih(namaField: RegExp, namaOpsi: RegExp) {
    await userEvent.click(screen.getByRole("combobox", { name: namaField }));
    await userEvent.click(await screen.findByRole("option", { name: namaOpsi }));
  }

  it("submit mengirim product_id, material_id, qty", async () => {
    const onSubmit = vi.fn();
    render(<BomForm products={PRODUCTS} materials={MATERIALS} onSubmit={onSubmit} />);

    await pilih(/^produk$/i, /KBYPL 200/);
    await pilih(/^material$/i, /BTL-200/);
    await userEvent.type(screen.getByLabelText(/qty per unit/i), "2.5");
    await userEvent.click(screen.getByRole("button", { name: /simpan/i }));

    await waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith({
        product_id: "p1",
        material_id: "m1",
        qty_per_unit: 2.5,
      }),
    );
  });
});
