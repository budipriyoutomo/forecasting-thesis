import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TableSkeleton } from "@/components/common/TableSkeleton";

describe("TableSkeleton", () => {
  it("merender jumlah baris yang diminta", () => {
    const { container } = render(<TableSkeleton rows={3} columns={4} />);

    expect(container.querySelectorAll("[data-slot='skeleton-row']").length).toBe(3);
  });

  // Placeholder murni visual — screen reader cukup diberi tahu bahwa data sedang dimuat,
  // bukan membacakan puluhan kotak kosong.
  it("mengumumkan status memuat dan menyembunyikan placeholder dari screen reader", () => {
    const { container } = render(<TableSkeleton rows={2} columns={2} />);

    expect(screen.getByRole("status")).toBeDefined();
    expect(screen.getByText("Memuat data…")).toBeDefined();
    expect(container.querySelector("[data-slot='skeleton-grid']")?.getAttribute("aria-hidden")).toBe(
      "true",
    );
  });
});
