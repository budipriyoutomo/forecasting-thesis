import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { LatestStockTable } from "@/components/inventory/LatestStockTable";
import { ReceiptForm } from "@/components/inventory/ReceiptForm";
import { ReceiptsTable } from "@/components/inventory/ReceiptsTable";
import { WasteFactorTable } from "@/components/inventory/WasteFactorTable";

const MATERIALS = [
  { id: "m1", code: "CAP-WHITE", name: "Cap White", unit: "PCS" },
  { id: "m2", code: "BTL-WHITE", name: "Bottle White", unit: "PCS" },
] as never[];

describe("Persediaan material (Fase 11.1/11.5)", () => {
  it("stok ERP terakhir per material + material tanpa snapshot", () => {
    render(<LatestStockTable latest={[{ material_id: "m1", snapshot_date: "2026-10-01", qty: 1200 }]} materials={MATERIALS} />);
    expect(screen.getByText("CAP-WHITE")).toBeDefined();
    expect(screen.getByText("1.200")).toBeDefined();
    expect(screen.getByText(/belum ada snapshot/i)).toBeDefined(); // BTL-WHITE
  });

  it("form kedatangan manual: validasi & submit", async () => {
    const onSubmit = vi.fn();
    render(<ReceiptForm materials={MATERIALS} onSubmit={onSubmit} />);
    await userEvent.click(screen.getByRole("button", { name: /simpan kedatangan/i }));
    expect(await screen.findByText(/material wajib dipilih/i)).toBeDefined();

    await userEvent.selectOptions(screen.getByLabelText(/^material$/i), "m2");
    await userEvent.type(screen.getByLabelText(/tanggal kedatangan/i), "2026-11-20");
    await userEvent.type(screen.getByLabelText(/^qty$/i), "300");
    await userEvent.type(screen.getByLabelText(/catatan/i), "PO-77");
    await userEvent.click(screen.getByRole("button", { name: /simpan kedatangan/i }));
    expect(onSubmit).toHaveBeenCalledWith({ material_id: "m2", expected_date: "2026-11-20", qty: 300, note: "PO-77" });
  });

  it("tabel kedatangan menampilkan sumber & aksi hapus", () => {
    render(
      <ReceiptsTable
        receipts={[{ id: "r1", material_id: "m1", expected_date: "2026-11-05", qty: 500, source: "upload", note: null }]}
        materials={MATERIALS}
        onDelete={vi.fn()}
      />,
    );
    expect(screen.getByText(/upload/i)).toBeDefined();
    expect(screen.getByRole("button", { name: /hapus/i })).toBeDefined();
  });

  it("faktor waste & persentase buffer", () => {
    render(<WasteFactorTable factors={[{ material_id: "m1", waste_factor: 1.03 }, { material_id: "m2", waste_factor: null }]} materials={MATERIALS} />);
    expect(screen.getByText("1.030")).toBeDefined();
    expect(screen.getByText("+3.0%")).toBeDefined();
    expect(screen.getByText(/standar 0/i)).toBeDefined();
  });
});
