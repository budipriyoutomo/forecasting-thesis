import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { WarehouseConfigForm } from "@/components/warehouse/WarehouseConfigForm";
import type { WarehouseConfig } from "@/types/warehouse";
import type { Product } from "@/types/product";

const PRODUCTS: Product[] = [
  { id: "p1", code: "KBYPL 200", name: "KIN Yogurt 200ml", category: null, unit: "PCS" },
  { id: "p2", code: "KBYST 200", name: "KIN Yogurt Strawberry 200ml", category: null, unit: "PCS" },
];

afterEach(() => vi.restoreAllMocks());

async function pilihProduk(namaOpsi: RegExp) {
  await userEvent.click(screen.getByRole("combobox", { name: /^produk$/i }));
  await userEvent.click(await screen.findByRole("option", { name: namaOpsi }));
}

describe("WarehouseConfigForm", () => {
  it("validasi produk wajib dipilih & kapasitas harus > 0", async () => {
    const onSubmit = vi.fn();
    render(<WarehouseConfigForm products={PRODUCTS} onSubmit={onSubmit} />);

    await userEvent.click(screen.getByRole("button", { name: /simpan/i }));

    expect(await screen.findByText(/produk wajib dipilih/i)).toBeDefined();
    expect(await screen.findByText(/harus lebih dari 0/i)).toBeDefined();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("submit mengirim product_id & capacity_qty bebas (bukan turunan palet)", async () => {
    const onSubmit = vi.fn();
    render(<WarehouseConfigForm products={PRODUCTS} onSubmit={onSubmit} />);

    await pilihProduk(/KBYST 200/);
    await userEvent.type(screen.getByLabelText(/kapasitas/i), "500000");
    await userEvent.click(screen.getByRole("button", { name: /simpan/i }));

    await waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith({ product_id: "p2", capacity_qty: 500000 }),
    );
  });

  it("mode ubah: field produk terkunci ke produk yang sudah ada, hanya kapasitas yang bisa diubah", async () => {
    const onSubmit = vi.fn();
    const initial: WarehouseConfig = { id: "c1", product_id: "p1", capacity_qty: "300000" };
    render(<WarehouseConfigForm products={PRODUCTS} initial={initial} onSubmit={onSubmit} />);

    expect(screen.getByRole("combobox", { name: /^produk$/i })).toHaveProperty("disabled", true);
    expect(screen.getByLabelText(/kapasitas/i)).toHaveProperty("value", "300000");

    await userEvent.clear(screen.getByLabelText(/kapasitas/i));
    await userEvent.type(screen.getByLabelText(/kapasitas/i), "450000");
    await userEvent.click(screen.getByRole("button", { name: /simpan/i }));

    await waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith({ product_id: "p1", capacity_qty: 450000 }),
    );
  });
});
