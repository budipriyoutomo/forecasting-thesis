import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SidebarNav } from "@/components/layout/SidebarNav";

const mockPathname = vi.fn(() => "/dashboard");
vi.mock("next/navigation", () => ({ usePathname: () => mockPathname() }));

describe("SidebarNav", () => {
  it("menampilkan semua menu utama", () => {
    render(<SidebarNav />);

    for (const label of ["Dashboard", "Produk", "Material", "BOM", "Forecast", "Gudang"]) {
      expect(screen.getByRole("link", { name: label })).toBeDefined();
    }
  });

  it("menandai menu aktif sesuai path", () => {
    mockPathname.mockReturnValue("/materials");
    render(<SidebarNav />);

    expect(screen.getByRole("link", { name: "Material" }).getAttribute("aria-current")).toBe("page");
    expect(screen.getByRole("link", { name: "Produk" }).getAttribute("aria-current")).toBeNull();
  });

  it("menandai menu aktif untuk sub-route", () => {
    mockPathname.mockReturnValue("/forecast/new/config");
    render(<SidebarNav />);

    expect(screen.getByRole("link", { name: "Forecast" }).getAttribute("aria-current")).toBe("page");
  });
});
