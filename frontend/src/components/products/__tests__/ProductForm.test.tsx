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
      selling_price: null,
    });
  });

  it("hanya ada satu isian harga produk (tanpa HPP), dikirim sebagai angka", async () => {
    const onSubmit = vi.fn();
    render(<ProductForm onSubmit={onSubmit} />);

    await userEvent.type(screen.getByLabelText(/kode sku/i), "KBYPL 200");
    await userEvent.type(screen.getByLabelText(/^nama$/i), "KIN Yogurt 200ml");
    await userEvent.type(screen.getByLabelText(/^satuan$/i), "PCS");
    expect(screen.queryByLabelText(/hpp/i)).toBeNull();
    await userEvent.type(screen.getByLabelText(/harga produk/i), "6000");
    await userEvent.click(screen.getByRole("button", { name: /simpan/i }));

    const sent = onSubmit.mock.calls[0][0];
    expect(sent.selling_price).toBe(6000);
    expect(sent).not.toHaveProperty("cost_price");
  });

  it("harga negatif ditolak", async () => {
    const onSubmit = vi.fn();
    render(<ProductForm onSubmit={onSubmit} />);

    await userEvent.type(screen.getByLabelText(/kode sku/i), "A");
    await userEvent.type(screen.getByLabelText(/^nama$/i), "A");
    await userEvent.type(screen.getByLabelText(/^satuan$/i), "PCS");
    await userEvent.type(screen.getByLabelText(/harga produk/i), "-1");
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
      selling_price: "6000.0000",
    };
    render(<ProductForm initial={product} onSubmit={vi.fn()} />);

    expect((screen.getByLabelText(/harga produk/i) as HTMLInputElement).value).toBe("6000");

    expect((screen.getByLabelText(/kode sku/i) as HTMLInputElement).value).toBe("KBYPL 700");
    expect((screen.getByLabelText(/^nama$/i) as HTMLInputElement).value).toBe("KIN Yogurt 700ml");
  });
});
