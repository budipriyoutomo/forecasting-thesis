import { describe, expect, it } from "vitest";

import { NAV_GROUPS, breadcrumbsFor, isActive } from "@/lib/navigation";

describe("NAV_GROUPS", () => {
  it("mengelompokkan menu mengikuti alur kerja PPIC", () => {
    expect(NAV_GROUPS.map((g) => g.label)).toEqual(["Utama", "Master Data", "Operasional"]);
  });

  it("memuat seluruh menu utama tanpa duplikat href", () => {
    const hrefs = NAV_GROUPS.flatMap((g) => g.items.map((i) => i.href));
    expect(hrefs).toEqual([
      "/dashboard",
      "/products",
      "/materials",
      "/boms",
      "/forecast/new",
      "/warehouse",
    ]);
    expect(new Set(hrefs).size).toBe(hrefs.length);
  });

  it("setiap menu punya ikon", () => {
    for (const item of NAV_GROUPS.flatMap((g) => g.items)) {
      expect(item.icon).toBeTruthy();
    }
  });
});

describe("isActive", () => {
  it("cocok pada path persis", () => {
    expect(isActive("/materials", "/materials")).toBe(true);
  });

  it("cocok pada sub-route", () => {
    expect(isActive("/forecast/new/config", "/forecast/new")).toBe(true);
  });

  it("tidak cocok pada prefix yang kebetulan sama", () => {
    // "/materials-lama" bukan sub-route "/materials".
    expect(isActive("/materials-lama", "/materials")).toBe(false);
  });

  it("tidak cocok pada menu lain", () => {
    expect(isActive("/materials", "/products")).toBe(false);
  });
});

describe("breadcrumbsFor", () => {
  it("menu tingkat atas hanya menghasilkan satu jejak", () => {
    expect(breadcrumbsFor("/dashboard")).toEqual([{ label: "Dashboard", href: "/dashboard" }]);
  });

  it("menyertakan label grup sebagai jejak tanpa tautan", () => {
    expect(breadcrumbsFor("/products")).toEqual([
      { label: "Master Data" },
      { label: "Produk", href: "/products" },
    ]);
  });

  it("menambahkan jejak sub-halaman tanpa tautan", () => {
    expect(breadcrumbsFor("/forecast/new/config")).toEqual([
      { label: "Operasional" },
      { label: "Forecast", href: "/forecast/new" },
      { label: "Konfigurasi" },
    ]);
  });

  it("path tak dikenal menghasilkan jejak kosong", () => {
    expect(breadcrumbsFor("/entah")).toEqual([]);
  });
});
