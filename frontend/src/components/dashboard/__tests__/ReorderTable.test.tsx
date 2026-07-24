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
