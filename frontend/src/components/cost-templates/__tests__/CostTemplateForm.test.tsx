import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CostTemplateForm } from "@/components/cost-templates/CostTemplateForm";

import { TEMPLATE } from "./fixtures";

describe("CostTemplateForm", () => {
  it("validasi nama, biaya pesan & biaya simpan wajib", async () => {
    const onSubmit = vi.fn();
    render(<CostTemplateForm onSubmit={onSubmit} />);

    await userEvent.click(screen.getByRole("button", { name: /simpan template/i }));

    expect(await screen.findByText(/nama wajib diisi/i)).toBeDefined();
    expect(screen.getAllByText(/wajib diisi/i).length).toBeGreaterThanOrEqual(3);
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("submit S, H, overhead & aset penyimpanan dengan pratinjau biaya per bulan", async () => {
    const onSubmit = vi.fn();
    render(<CostTemplateForm onSubmit={onSubmit} />);

    await userEvent.type(screen.getByLabelText(/^nama template$/i), "Template 2026");
    await userEvent.type(screen.getByLabelText(/biaya pesan/i), "250000");
    await userEvent.type(screen.getByLabelText(/biaya simpan/i), "800");

    await userEvent.click(screen.getByRole("button", { name: /tambah overhead/i }));
    const overhead = screen.getByRole("group", { name: /overhead 1/i });
    await userEvent.type(within(overhead).getByLabelText(/^nama$/i), "Listrik");
    await userEvent.type(within(overhead).getByLabelText(/biaya per bulan/i), "3000000");

    await userEvent.click(screen.getByRole("button", { name: /tambah aset/i }));
    const asset = screen.getByRole("group", { name: /aset 1/i });
    await userEvent.type(within(asset).getByLabelText(/^nama$/i), "Rak");
    await userEvent.type(within(asset).getByLabelText(/harga beli/i), "50000000");
    await userEvent.type(within(asset).getByLabelText(/nilai sisa/i), "5000000");
    await userEvent.type(within(asset).getByLabelText(/umur/i), "60");
    await userEvent.clear(within(asset).getByLabelText(/jumlah/i));
    await userEvent.type(within(asset).getByLabelText(/jumlah/i), "10");
    // (50jt − 5jt) ÷ 60 × 10 = 7,5 jt per bulan
    expect(within(asset).getByText("Rp 7.500.000 / bulan")).toBeDefined();

    await userEvent.click(screen.getByRole("button", { name: /simpan template/i }));

    await waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith({
        name: "Template 2026",
        description: null,
        ordering_cost: 250000,
        holding_cost: 800,
        items: [
          {
            item_type: "OVERHEAD",
            name: "Listrik",
            monthly_amount: 3000000,
            purchase_price: null,
            salvage_value: null,
            useful_life_months: null,
            qty: 1,
          },
          {
            item_type: "STORAGE_ASSET",
            name: "Rak",
            monthly_amount: null,
            purchase_price: 50000000,
            salvage_value: 5000000,
            useful_life_months: 60,
            qty: 10,
          },
        ],
      }),
    );
  });

  it("aset wajib harga beli & umur; nilai sisa tak boleh melebihi harga beli", async () => {
    const onSubmit = vi.fn();
    render(<CostTemplateForm onSubmit={onSubmit} />);
    await userEvent.type(screen.getByLabelText(/^nama template$/i), "T");
    await userEvent.type(screen.getByLabelText(/biaya pesan/i), "1");
    await userEvent.type(screen.getByLabelText(/biaya simpan/i), "1");
    await userEvent.click(screen.getByRole("button", { name: /tambah aset/i }));
    const asset = screen.getByRole("group", { name: /aset 1/i });
    await userEvent.type(within(asset).getByLabelText(/^nama$/i), "Rak");
    await userEvent.type(within(asset).getByLabelText(/harga beli/i), "1000");
    await userEvent.type(within(asset).getByLabelText(/nilai sisa/i), "2000");
    await userEvent.click(screen.getByRole("button", { name: /simpan template/i }));

    expect(await within(asset).findByText(/umur wajib diisi/i)).toBeDefined();
    expect(within(asset).getByText(/tidak boleh melebihi harga beli/i)).toBeDefined();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("mode ubah: nilai & item terisi, item bisa dihapus", async () => {
    const onSubmit = vi.fn();
    render(<CostTemplateForm initial={TEMPLATE} onSubmit={onSubmit} />);

    expect(screen.getByLabelText(/^nama template$/i)).toHaveProperty("value", "Template 2026");
    expect(screen.getByLabelText(/biaya simpan/i)).toHaveProperty("value", "800");
    const overhead = screen.getByRole("group", { name: /overhead 1/i });
    await userEvent.click(within(overhead).getByRole("button", { name: /hapus item/i }));
    await userEvent.click(screen.getByRole("button", { name: /simpan template/i }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    const items = onSubmit.mock.calls[0][0].items;
    expect(items.map((i: { name: string }) => i.name)).toEqual(["Rak"]);
  });
});
