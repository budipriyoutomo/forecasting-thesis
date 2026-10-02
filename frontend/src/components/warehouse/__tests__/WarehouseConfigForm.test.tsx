import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { WarehouseConfigForm } from "@/components/warehouse/WarehouseConfigForm";
import type { WarehouseConfig } from "@/types/warehouse";
import type { Product } from "@/types/product";

const PRODUCTS: Product[] = [
  { id: "p1", code: "KBYPL 200", name: "KIN Yogurt 200ml", category: null, unit: "PCS" },
  { id: "p2", code: "KBYST 200", name: "KIN Yogurt Strawberry 200ml", category: null, unit: "Dus" },
];

afterEach(() => vi.restoreAllMocks());

async function pilih(label: RegExp, namaOpsi: RegExp) {
  await userEvent.click(screen.getByRole("combobox", { name: label }));
  await userEvent.click(await screen.findByRole("option", { name: namaOpsi }));
}

describe("WarehouseConfigForm", () => {
  it("validasi produk wajib dipilih & jumlah dus harus > 0", async () => {
    const onSubmit = vi.fn();
    render(<WarehouseConfigForm products={PRODUCTS} onSubmit={onSubmit} />);

    await userEvent.click(screen.getByRole("button", { name: /simpan/i }));

    expect(await screen.findByText(/produk wajib dipilih/i)).toBeDefined();
    expect(await screen.findByText(/kapasitas harus lebih dari 0/i)).toBeDefined();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("mode dus untuk produk unit dus: tanpa isian pcs/dus, submit input pallet/dus", async () => {
    const onSubmit = vi.fn();
    render(<WarehouseConfigForm products={PRODUCTS} onSubmit={onSubmit} />);

    await pilih(/^produk$/i, /KBYST 200/);
    expect(screen.queryByLabelText(/pcs per dus/i)).toBeNull();
    expect(screen.queryByLabelText(/jumlah pallet/i)).toBeNull();
    await userEvent.type(screen.getByLabelText(/jumlah dus/i), "500");
    expect(screen.getByText(/500 dus/i)).toBeDefined();
    await userEvent.click(screen.getByRole("button", { name: /simpan/i }));

    await waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith({
        product_id: "p2",
        capacity_mode: "DUS",
        pallet_qty: 0,
        dus_qty: 500,
        dus_per_pallet: null,
        pcs_per_dus: null,
      }),
    );
  });

  it("mode kombinasi untuk produk PCS: semua field muncul + pratinjau kapasitas efektif", async () => {
    const onSubmit = vi.fn();
    render(<WarehouseConfigForm products={PRODUCTS} onSubmit={onSubmit} />);

    await pilih(/^produk$/i, /KBYPL 200/);
    await pilih(/mode kapasitas/i, /kombinasi/i);
    await userEvent.type(screen.getByLabelText(/jumlah pallet/i), "10");
    await userEvent.type(screen.getByLabelText(/dus per pallet/i), "60");
    await userEvent.type(screen.getByLabelText(/jumlah dus/i), "25");
    await userEvent.type(screen.getByLabelText(/pcs per dus/i), "24");

    // (10 × 60 + 25) = 625 dus × 24 = 15.000 PCS
    expect(screen.getByText(/625 dus/i)).toBeDefined();
    expect(screen.getByText(/15\.000 PCS/)).toBeDefined();

    await userEvent.click(screen.getByRole("button", { name: /simpan/i }));
    await waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith({
        product_id: "p1",
        capacity_mode: "COMBINED",
        pallet_qty: 10,
        dus_qty: 25,
        dus_per_pallet: 60,
        pcs_per_dus: 24,
      }),
    );
  });

  it("mode pallet wajib isi dus per pallet; produk PCS wajib isi pcs per dus", async () => {
    const onSubmit = vi.fn();
    render(<WarehouseConfigForm products={PRODUCTS} onSubmit={onSubmit} />);

    await pilih(/^produk$/i, /KBYPL 200/);
    await pilih(/mode kapasitas/i, /^pallet$/i);
    await userEvent.type(screen.getByLabelText(/jumlah pallet/i), "10");
    await userEvent.click(screen.getByRole("button", { name: /simpan/i }));

    expect(await screen.findByText(/dus per pallet wajib diisi/i)).toBeDefined();
    expect(await screen.findByText(/pcs per dus wajib diisi/i)).toBeDefined();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("mode ubah: produk terkunci, nilai pallet/dus terisi dari data tersimpan", async () => {
    const onSubmit = vi.fn();
    const initial: WarehouseConfig = {
      id: "c1",
      product_id: "p1",
      capacity_mode: "PALLET",
      pallet_qty: "4",
      dus_qty: "0",
      dus_per_pallet: "50",
      pcs_per_dus: "6",
      capacity_dus: "200",
      capacity_qty: "1200",
      uom: "PCS",
    };
    render(<WarehouseConfigForm products={PRODUCTS} initial={initial} onSubmit={onSubmit} />);

    expect(screen.getByRole("combobox", { name: /^produk$/i })).toHaveProperty("disabled", true);
    expect(screen.getByLabelText(/jumlah pallet/i)).toHaveProperty("value", "4");
    expect(screen.getByLabelText(/pcs per dus/i)).toHaveProperty("value", "6");

    await userEvent.clear(screen.getByLabelText(/jumlah pallet/i));
    await userEvent.type(screen.getByLabelText(/jumlah pallet/i), "5");
    await userEvent.click(screen.getByRole("button", { name: /simpan/i }));

    await waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith({
        product_id: "p1",
        capacity_mode: "PALLET",
        pallet_qty: 5,
        dus_qty: 0,
        dus_per_pallet: 50,
        pcs_per_dus: 6,
      }),
    );
  });
});
