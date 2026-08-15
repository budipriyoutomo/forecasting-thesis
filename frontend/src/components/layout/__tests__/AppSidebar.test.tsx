import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AppSidebar } from "@/components/layout/AppSidebar";
import { SidebarProvider } from "@/components/ui/sidebar";

const mockPathname = vi.fn(() => "/dashboard");
vi.mock("next/navigation", () => ({ usePathname: () => mockPathname() }));

function renderSidebar() {
  return render(
    <SidebarProvider>
      <AppSidebar />
    </SidebarProvider>,
  );
}

describe("AppSidebar", () => {
  it("menampilkan semua menu utama", () => {
    mockPathname.mockReturnValue("/dashboard");
    renderSidebar();

    for (const label of ["Dashboard", "Produk", "Material", "BOM", "Forecast", "Gudang"]) {
      expect(screen.getByRole("link", { name: label })).toBeDefined();
    }
  });

  it("menampilkan label grup", () => {
    mockPathname.mockReturnValue("/dashboard");
    renderSidebar();

    expect(screen.getByText("Master Data")).toBeDefined();
    expect(screen.getByText("Operasional")).toBeDefined();
  });

  it("menandai menu aktif sesuai path", () => {
    mockPathname.mockReturnValue("/materials");
    renderSidebar();

    expect(screen.getByRole("link", { name: "Material" }).getAttribute("aria-current")).toBe("page");
    expect(screen.getByRole("link", { name: "Produk" }).getAttribute("aria-current")).toBeNull();
  });

  it("menandai menu aktif untuk sub-route", () => {
    mockPathname.mockReturnValue("/forecast/new/config");
    renderSidebar();

    expect(screen.getByRole("link", { name: "Forecast" }).getAttribute("aria-current")).toBe("page");
  });

  it("menautkan brand ke dashboard", () => {
    mockPathname.mockReturnValue("/dashboard");
    renderSidebar();

    expect(screen.getByRole("link", { name: /forecastiq/i }).getAttribute("href")).toBe("/dashboard");
  });
});
