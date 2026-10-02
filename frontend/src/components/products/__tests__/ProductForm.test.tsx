import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProductForm } from "@/components/products/ProductForm";
import type { Product } from "@/types/product";

afterEach(() => vi.restoreAllMocks());

describe("ProductForm", () => {
  it("validasi field wajib tanpa memanggil onSubmit", async () => {
    const onSubmit = vi.fn();
    render(<ProductForm onSubmit={onSubmit} />);

    await userEvent.click(screen.getByRole("button", { name: /simpan/i }));

    expect(await screen.findByText(/Kode wajib diisi/i)).toBeDefined();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("submit mengirim input yang benar (category kosong -> null)", async () => {
    const onSubmit = vi.fn();
    render(<ProductForm onSubmit={onSubmit} />);

    await userEvent.type(screen.getByLabelText(/kode sku/i), "KBYPL 200");
    await userEvent.type(screen.getByLabelText(/^nama$/i), "KIN Yogurt 200ml");
    await userEvent.type(screen.getByLabelText(/^satuan$/i), "PCS");
    await userEvent.click(screen.getByRole("button", { name: /simpan/i }));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith({
      code: "KBYPL 200",
      name: "KIN Yogurt 200ml",
      category: null,
      unit: "PCS",
      cost_price: null,
      selling_price: null,
    });
  });

  it("mengirim HPP & harga jual sebagai angka (Rupiah)", async () => {
    const onSubmit = vi.fn();
    render(<ProductForm onSubmit={onSubmit} />);

    await userEvent.type(screen.getByLabelText(/kode sku/i), "KBYPL 200");
    await userEvent.type(screen.getByLabelText(/^nama$/i), "KIN Yogurt 200ml");
    await userEvent.type(screen.getByLabelText(/^satuan$/i), "PCS");
    await userEvent.type(screen.getByLabelText(/hpp/i), "4500");
    await userEvent.type(screen.getByLabelText(/harga jual/i), "6000");
    await userEvent.click(screen.getByRole("button", { name: /simpan/i }));

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ cost_price: 4500, selling_price: 6000 }),
    );
  });

  it("harga negatif ditolak", async () => {
    const onSubmit = vi.fn();
    render(<ProductForm onSubmit={onSubmit} />);

    await userEvent.type(screen.getByLabelText(/kode sku/i), "A");
    await userEvent.type(screen.getByLabelText(/^nama$/i), "A");
    await userEvent.type(screen.getByLabelText(/^satuan$/i), "PCS");
    await userEvent.type(screen.getByLabelText(/harga jual/i), "-1");
    await userEvent.click(screen.getByRole("button", { name: /simpan/i }));

    expect(await screen.findByText(/tidak boleh negatif/i)).toBeDefined();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("mengisi nilai awal saat mode edit", () => {
    const product: Product = {
      id: "p1",
      code: "KBYPL 700",
      name: "KIN Yogurt 700ml",
      category: "RTD Yogurt",
      unit: "PCS",
      cost_price: "4500.0000",
      selling_price: null,
    };
    render(<ProductForm initial={product} onSubmit={vi.fn()} />);

    expect((screen.getByLabelText(/hpp/i) as HTMLInputElement).value).toBe("4500");
    expect((screen.getByLabelText(/harga jual/i) as HTMLInputElement).value).toBe("");

    expect((screen.getByLabelText(/kode sku/i) as HTMLInputElement).value).toBe("KBYPL 700");
    expect((screen.getByLabelText(/^nama$/i) as HTMLInputElement).value).toBe("KIN Yogurt 700ml");
  });
});
