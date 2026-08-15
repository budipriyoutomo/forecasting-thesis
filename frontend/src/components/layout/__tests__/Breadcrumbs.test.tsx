import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Breadcrumbs } from "@/components/layout/Breadcrumbs";

const mockPathname = vi.fn(() => "/dashboard");
vi.mock("next/navigation", () => ({ usePathname: () => mockPathname() }));

describe("Breadcrumbs", () => {
  it("menampilkan jejak halaman saat ini", () => {
    mockPathname.mockReturnValue("/forecast/new/config");
    render(<Breadcrumbs />);

    expect(screen.getByText("Operasional")).toBeDefined();
    expect(screen.getByRole("link", { name: "Forecast" }).getAttribute("href")).toBe("/forecast/new");
    expect(screen.getByText("Konfigurasi")).toBeDefined();
  });

  // BreadcrumbPage shadcn memakai <span role="link" aria-disabled>, jadi yang
  // membedakannya dari tautan sungguhan adalah ketiadaan href, bukan role-nya.
  it("jejak terakhir ditandai sebagai halaman saat ini, bukan tautan", () => {
    mockPathname.mockReturnValue("/products");
    render(<Breadcrumbs />);

    const current = screen.getByText("Produk");
    expect(current.tagName).toBe("SPAN");
    expect(current.getAttribute("href")).toBeNull();
    expect(current.getAttribute("aria-current")).toBe("page");
    expect(current.getAttribute("aria-disabled")).toBe("true");
  });

  it("label grup tidak ditandai sebagai halaman saat ini", () => {
    mockPathname.mockReturnValue("/products");
    render(<Breadcrumbs />);

    expect(screen.getByText("Master Data").getAttribute("aria-current")).toBeNull();
  });

  it("tidak merender apa pun untuk path tak dikenal", () => {
    mockPathname.mockReturnValue("/entah");
    const { container } = render(<Breadcrumbs />);

    expect(container.firstChild).toBeNull();
  });
});
