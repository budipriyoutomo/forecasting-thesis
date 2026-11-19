import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { BomMultiForm } from "@/components/boms/BomMultiForm";
import type { Material } from "@/types/material";
import type { Product } from "@/types/product";

const PRODUCTS: Product[] = [{ id: "p1", code: "KBYPL 200", name: "KIN Yogurt", category: null, unit: "PCS" }];
const base = { unit: "PCS", lead_time_days: 7, moq: "0", manual_safety_stock: null, category: null };
const MATERIALS: Material[] = [
  { ...base, id: "m1", code: "CAP-BLUE", name: "Cap Blue" },
  { ...base, id: "m2", code: "BTL-WHITE", name: "Bottle White" },
];

async function pilih(nama: RegExp, opsi: RegExp) {
  await userEvent.click(screen.getByRole("combobox", { name: nama }));
  await userEvent.click(await screen.findByRole("option", { name: opsi }));
}

describe("BomMultiForm", () => {
  it("input lebih dari satu material untuk satu produk sekaligus", async () => {
    const onSubmit = vi.fn();
    render(<BomMultiForm products={PRODUCTS} materials={MATERIALS} onSubmit={onSubmit} />);

    await pilih(/^produk$/i, /KBYPL 200/);
    await pilih(/^material 1$/i, /CAP-BLUE/);
    await userEvent.type(screen.getByLabelText(/^qty 1$/i), "1");
    await userEvent.click(screen.getByRole("button", { name: /tambah material/i }));
    await pilih(/^material 2$/i, /BTL-WHITE/);
    await userEvent.type(screen.getByLabelText(/^qty 2$/i), "2");
    await userEvent.click(screen.getByRole("button", { name: /simpan/i }));

    await waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith({
        product_id: "p1",
        items: [
          { material_id: "m1", qty_per_unit: 1 },
          { material_id: "m2", qty_per_unit: 2 },
        ],
      }),
    );
  });

  it("menolak material yang sama dua kali", async () => {
    const onSubmit = vi.fn();
    render(<BomMultiForm products={PRODUCTS} materials={MATERIALS} onSubmit={onSubmit} />);

    await pilih(/^produk$/i, /KBYPL 200/);
    await pilih(/^material 1$/i, /CAP-BLUE/);
    await userEvent.type(screen.getByLabelText(/^qty 1$/i), "1");
    await userEvent.click(screen.getByRole("button", { name: /tambah material/i }));
    await pilih(/^material 2$/i, /CAP-BLUE/);
    await userEvent.type(screen.getByLabelText(/^qty 2$/i), "1");
    await userEvent.click(screen.getByRole("button", { name: /simpan/i }));

    expect(await screen.findByText(/material sudah dipilih/i)).toBeDefined();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("baris material bisa dihapus selama masih tersisa satu", async () => {
    render(<BomMultiForm products={PRODUCTS} materials={MATERIALS} onSubmit={vi.fn()} />);
    expect(screen.queryByRole("button", { name: /hapus baris 1/i })).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: /tambah material/i }));
    await userEvent.click(screen.getByRole("button", { name: /hapus baris 2/i }));
    expect(screen.queryByLabelText(/^qty 2$/i)).toBeNull();
  });
});
