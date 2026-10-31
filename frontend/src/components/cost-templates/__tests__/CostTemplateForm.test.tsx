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
        holding_cost_rate_pct: null, // Fase 11.4 — i (%) kosong
        items: [
          {
            item_type: "OVERHEAD",
            name: "Listrik",
            monthly_amount: 3000000,
            purchase_price: null,
            salvage_value: null,
            useful_life_months: null,
            qty: 1,
            period_basis: "monthly",
          },
          {
            item_type: "STORAGE_ASSET",
            name: "Rak",
            monthly_amount: null,
            purchase_price: 50000000,
            salvage_value: 5000000,
            useful_life_months: 60,
            qty: 10,
            period_basis: "monthly",
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

  it("i (%) EOQ klasik + item perawatan basis tahunan (Fase 11.4)", async () => {
    const onSubmit = vi.fn();
    render(<CostTemplateForm onSubmit={onSubmit} />);

    await userEvent.type(screen.getByLabelText(/^nama template$/i), "Template thesis");
    await userEvent.type(screen.getByLabelText(/biaya pesan/i), "250000");
    await userEvent.type(screen.getByLabelText(/biaya simpan \/ unit/i), "0");
    await userEvent.type(screen.getByLabelText(/i \(%\)/i), "20");

    await userEvent.click(screen.getByRole("button", { name: /tambah perawatan/i }));
    const m = screen.getByRole("group", { name: /perawatan 1/i });
    await userEvent.type(within(m).getByLabelText(/^nama$/i), "Perawatan forklift");
    await userEvent.type(within(m).getByLabelText(/biaya per bulan/i), "1200000");
    await userEvent.click(within(m).getByRole("radio", { name: /per tahun/i }));
    expect(within(m).getByText(/100\.000/)).toBeDefined(); // 1,2 jt ÷ 12 per bulan

    await userEvent.click(screen.getByRole("button", { name: /simpan template/i }));
    await waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          holding_cost_rate_pct: 20,
          items: [
            expect.objectContaining({
              item_type: "MAINTENANCE", monthly_amount: 1200000, period_basis: "annual", purchase_price: null,
            }),
          ],
        }),
      ),
    );
  });

  it("i (%) di luar 0–100 ditolak", async () => {
    const onSubmit = vi.fn();
    render(<CostTemplateForm onSubmit={onSubmit} />);
    await userEvent.type(screen.getByLabelText(/^nama template$/i), "T");
    await userEvent.type(screen.getByLabelText(/biaya pesan/i), "1");
    await userEvent.type(screen.getByLabelText(/biaya simpan \/ unit/i), "1");
    await userEvent.type(screen.getByLabelText(/i \(%\)/i), "150");
    await userEvent.click(screen.getByRole("button", { name: /simpan template/i }));

    expect(await screen.findByText(/antara 0 dan 100/i)).toBeDefined();
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
