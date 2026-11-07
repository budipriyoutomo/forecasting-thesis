import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { ReorderTable } from "@/components/dashboard/ReorderTable";
import type { ReorderRecommendation } from "@/types/reorder";

const RECS: ReorderRecommendation[] = [
  { material_id: "m1", safety_stock: "6.6", reorder_point: "46.6", recommended_order_qty: "87", status: "urgent" },
  { material_id: "m2", safety_stock: "3", reorder_point: "20", recommended_order_qty: "0", status: "safe" },
  { material_id: "m3", safety_stock: "2", reorder_point: "10", recommended_order_qty: "0", status: "overstock" },
];

describe("ReorderTable", () => {
  it("menampilkan semua rekomendasi awalnya", () => {
    render(<ReorderTable recommendations={RECS} />);

    expect(screen.getByText("m1")).toBeDefined();
    expect(screen.getByText("m2")).toBeDefined();
    expect(screen.getByText("m3")).toBeDefined();
  });

  it("filter status urgent hanya menampilkan yang urgent", async () => {
    render(<ReorderTable recommendations={RECS} />);

    await userEvent.click(screen.getByRole("button", { name: /Segera reorder/i }));

    expect(screen.getByText("m1")).toBeDefined();
    expect(screen.queryByText("m2")).toBeNull();
    expect(screen.queryByText("m3")).toBeNull();
  });

  it("menampilkan pesan kosong saat filter tanpa hasil", async () => {
    render(<ReorderTable recommendations={[RECS[0]]} />);

    await userEvent.click(screen.getByRole("button", { name: /Kelebihan stok/i }));

    expect(screen.getByText(/Tidak ada rekomendasi/i)).toBeDefined();
  });
});

describe("ReorderTable — Fase 11 (buffer, EOQ, status data)", () => {
  it("menampilkan buffer stock, EOQ + metode, dan peringatan data kurang", async () => {
    const { render, screen } = await import("@testing-library/react");
    const { ReorderTable } = await import("@/components/dashboard/ReorderTable");
    render(
      <ReorderTable
        recommendations={[
          {
            material_id: "m1", safety_stock: "47.8", reorder_point: "126.8", recommended_order_qty: "200",
            status: "urgent", buffer_stock: "9", waste_factor: "1.03", eoq_qty: "4473", eoq_method: "classic",
            item_status: "COMPLETED", stock_source: "snapshot", current_stock_used: "0",
          },
          {
            material_id: "m2", safety_stock: "1", reorder_point: "2", recommended_order_qty: "0",
            status: "safe", buffer_stock: "0", eoq_qty: "100", eoq_method: "dynamic",
            item_status: "MISSING_UNIT_PRICE", stock_source: "request", current_stock_used: "10",
          },
        ]}
      />,
    );
    expect(screen.getByRole("columnheader", { name: /buffer/i })).toBeDefined();
    expect(screen.getByText(/waste 3\.0%/i)).toBeDefined();
    expect(screen.getByText(/klasik/i)).toBeDefined();
    expect(screen.getByText(/harga material belum diisi/i)).toBeDefined();
    expect(screen.getByText(/stok erp/i)).toBeDefined();
  });
});

describe("ReorderTable — Fase 11.9 (sumber tunggal titik & qty pesan)", () => {
  it("satu kolom Qty pesan + label kebijakan; EOQ sebagai info; rumus ROP ditampilkan", () => {
    render(
      <ReorderTable
        recommendations={[
          {
            material_id: "m1", safety_stock: "20", reorder_point: "90", recommended_order_qty: "300",
            status: "urgent", eoq_qty: "300", eoq_method: "dynamic",
            rop_formula_used: "standard", order_qty_policy_used: "eoq", order_up_to_level: "160",
          },
          {
            material_id: "m2", safety_stock: "20", reorder_point: "95", recommended_order_qty: "165",
            status: "urgent", eoq_qty: "300", rop_formula_used: "with_buffer",
            order_qty_policy_used: "order_up_to", order_up_to_level: "165",
          },
        ]}
      />,
    );
    expect(screen.getByRole("columnheader", { name: /^qty pesan$/i })).toBeDefined();
    expect(screen.queryByRole("columnheader", { name: /^order qty$/i })).toBeNull();
    expect(screen.getByRole("columnheader", { name: /eoq \(info\)/i })).toBeDefined();
    expect(screen.getByText(/^kelipatan eoq$/i)).toBeDefined();
    expect(screen.getByText(/order-up-to S = 165/i)).toBeDefined();
    expect(screen.getByText("μ·L + SS")).toBeDefined();
    expect(screen.getByText("μ·L + SS + B")).toBeDefined();
  });

  it("rekomendasi lama tanpa kolom kebijakan tetap tampil tanpa label", () => {
    render(<ReorderTable recommendations={[RECS[0]]} />);
    expect(screen.getByText("87")).toBeDefined();
    expect(screen.queryByText(/kelipatan eoq/i)).toBeNull();
  });
});
