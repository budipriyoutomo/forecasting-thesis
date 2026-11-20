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
      "/warehouse",
      "/cost-templates",
      "/forecast-settings",
      "/external-variables",
      "/inventory",
      "/forecast",
      "/material-arrivals",
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

  it("kapasitas gudang & template biaya berada di grup Master Data (Fase 10)", () => {
    expect(breadcrumbsFor("/warehouse")).toEqual([
      { label: "Master Data" },
      { label: "Kapasitas Gudang", href: "/warehouse" },
    ]);
    expect(breadcrumbsFor("/cost-templates")).toEqual([
      { label: "Master Data" },
      { label: "Template Biaya", href: "/cost-templates" },
    ]);
  });

  // CR v3.6 §1 — /forecast = daftar run; sub-halaman wizard & detail run
  it("menambahkan jejak sub-halaman: wizard forecast baru", () => {
    expect(breadcrumbsFor("/forecast/new")).toEqual([
      { label: "Operasional" },
      { label: "Forecast", href: "/forecast" },
      { label: "Forecast baru" },
    ]);
    expect(breadcrumbsFor("/forecast/new/config")).toEqual([
      { label: "Operasional" },
      { label: "Forecast", href: "/forecast" },
      { label: "Forecast baru", href: "/forecast/new" },
      { label: "Konfigurasi" },
    ]);
  });

  it("detail run (segmen dinamis) berlabel 'Detail run'", () => {
    expect(breadcrumbsFor("/forecast/runs/3f2a")).toEqual([
      { label: "Operasional" },
      { label: "Forecast", href: "/forecast" },
      { label: "Detail run" },
    ]);
  });

  it("path tak dikenal menghasilkan jejak kosong", () => {
    expect(breadcrumbsFor("/entah")).toEqual([]);
  });
});
