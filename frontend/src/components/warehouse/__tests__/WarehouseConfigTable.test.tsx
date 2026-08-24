import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { WarehouseConfigTable } from "@/components/warehouse/WarehouseConfigTable";
import type { WarehouseConfig } from "@/types/warehouse";
import type { Product } from "@/types/product";

const products: Product[] = [
  { id: "p1", code: "KBYPL 200", name: "KIN Yogurt 200ml", category: null, unit: "PCS" },
];

const configs: WarehouseConfig[] = [{ id: "c1", product_id: "p1", capacity_qty: "600000" }];

describe("WarehouseConfigTable", () => {
  it("menampilkan kode — nama produk, bukan UUID", () => {
    render(<WarehouseConfigTable configs={configs} products={products} />);

    expect(screen.getByText("KBYPL 200 — KIN Yogurt 200ml")).toBeDefined();
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
