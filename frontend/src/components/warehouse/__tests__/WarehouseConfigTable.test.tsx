import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { WarehouseConfigTable } from "@/components/warehouse/WarehouseConfigTable";
import type { WarehouseConfig } from "@/types/warehouse";
import type { Product } from "@/types/product";

const products: Product[] = [
  { id: "p1", code: "KBYPL 200", name: "KIN Yogurt 200ml", category: null, unit: "PCS" },
];

const configs: WarehouseConfig[] = [
  {
    id: "c1",
    product_id: "p1",
    capacity_mode: "COMBINED",
    pallet_qty: "10",
    dus_qty: "25",
    dus_per_pallet: "60",
    pcs_per_dus: "24",
    capacity_dus: "625",
    capacity_qty: "15000",
    uom: "PCS",
  },
];

describe("WarehouseConfigTable", () => {
  it("menampilkan kode — nama produk, bukan UUID", () => {
    render(<WarehouseConfigTable configs={configs} products={products} />);

    expect(screen.getByText("KBYPL 200 — KIN Yogurt 200ml")).toBeDefined();
  });

  it("menampilkan mode, rincian pallet/dus, dan kapasitas efektif dalam unit produk", () => {
    render(<WarehouseConfigTable configs={configs} products={products} />);

    expect(screen.getByText("Kombinasi")).toBeDefined();
    expect(screen.getByText("10 pallet × 60 + 25 dus")).toBeDefined();
    expect(screen.getByText("625 dus")).toBeDefined();
    expect(screen.getByText("15.000 PCS")).toBeDefined();
  });

  it("jatuh ke product_id saat produk tidak ada di master data", () => {
    render(<WarehouseConfigTable configs={configs} products={[]} />);

    expect(screen.getByText("p1")).toBeDefined();
  });

  it("memanggil onEdit/onDelete dengan baris yang benar", async () => {
    const onEdit = vi.fn();
    const onDelete = vi.fn();
    const { default: userEvent } = await import("@testing-library/user-event");
    render(
      <WarehouseConfigTable configs={configs} products={products} onEdit={onEdit} onDelete={onDelete} />,
    );

    await userEvent.click(screen.getByRole("button", { name: /ubah/i }));
    expect(onEdit).toHaveBeenCalledWith(expect.objectContaining({ id: "c1", product_id: "p1" }));

    await userEvent.click(screen.getByRole("button", { name: /hapus/i }));
    expect(await screen.findByRole("button", { name: /ya, hapus/i })).toBeDefined();
  });
});
