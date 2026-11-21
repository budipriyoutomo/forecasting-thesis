import {
  Archive,
  Boxes,
  Calculator,
  CloudSun,
  LayoutDashboard,
  LineChart,
  Network,
  Package,
  SlidersHorizontal,
  Truck,
  Users,
  Warehouse,
  type LucideIcon,
} from "lucide-react";

import type { Action } from "@/lib/permissions";

// Sumber tunggal struktur navigasi: dipakai sidebar sekaligus breadcrumb, supaya
// keduanya tidak bisa saling tidak sinkron. Urutan grup mengikuti alur kerja PPIC —
// master data (produk → material → BOM → kapasitas gudang → template biaya →
// pengaturan forecast) dulu,
// baru operasional (forecast). Gudang & template biaya masuk Master Data sejak Fase 10.

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  /** Menu hanya tampil untuk role yang punya izin ini (CR v3.7); tanpa = semua role. */
  permission?: Action;
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

export const NAV_GROUPS: NavGroup[] = [
  {
    label: "Utama",
    items: [{ href: "/dashboard", label: "Dashboard", icon: LayoutDashboard }],
  },
  {
    label: "Master Data",
    items: [
      { href: "/products", label: "Produk", icon: Package },
      { href: "/materials", label: "Material", icon: Boxes },
      { href: "/boms", label: "BOM", icon: Network },
      { href: "/warehouse", label: "Kapasitas Gudang", icon: Warehouse },
      { href: "/cost-templates", label: "Template Biaya", icon: Calculator },
      { href: "/forecast-settings", label: "Pengaturan", icon: SlidersHorizontal },
      { href: "/external-variables", label: "Variabel Eksternal", icon: CloudSun },
    ],
  },
  {
    label: "Operasional",
    items: [
      { href: "/inventory", label: "Persediaan Material", icon: Archive },
      // CR v3.6 §1 — daftar run; forecast baru & detail run adalah sub-halamannya.
      { href: "/forecast", label: "Forecast", icon: LineChart },
      { href: "/material-arrivals", label: "Kedatangan Material", icon: Truck },
    ],
  },
  {
    label: "Administrasi",
    items: [{ href: "/users", label: "Manajemen User", icon: Users, permission: "user.manage" }],
  },
];

export function isActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

export interface Crumb {
  label: string;
  /** Tanpa href berarti jejak tidak bisa diklik: label grup, atau halaman saat ini. */
  href?: string;
}

// Jejak untuk halaman di bawah menu yang tidak punya entri sidebar sendiri. Urutan
// penting: pola lebih spesifik dulu. Segmen dinamis (id run) dicocokkan dengan regex.
const SUB_PAGES: { match: RegExp; trail: Crumb[] }[] = [
  {
    match: /^\/forecast\/new\/config$/,
    trail: [{ label: "Forecast baru", href: "/forecast/new" }, { label: "Konfigurasi" }],
  },
  { match: /^\/forecast\/new$/, trail: [{ label: "Forecast baru" }] },
  { match: /^\/forecast\/runs\/[^/]+$/, trail: [{ label: "Detail run" }] },
];

/** Label sub-halaman (dipakai test & judul) — kompatibel dengan peta lama. */
export const SUB_PAGE_LABELS: Record<string, string> = {
  "/forecast/new": "Forecast baru",
  "/forecast/new/config": "Konfigurasi",
  "/forecast/runs/[id]": "Detail run",
};

export function breadcrumbsFor(pathname: string): Crumb[] {
  for (const group of NAV_GROUPS) {
    for (const item of group.items) {
      if (!isActive(pathname, item.href)) continue;

      const crumbs: Crumb[] = [];
      // Grup "Utama" hanya wadah, bukan tingkatan yang berarti bagi user.
      if (group.label !== "Utama") crumbs.push({ label: group.label });
      crumbs.push({ label: item.label, href: item.href });

      const sub = SUB_PAGES.find((p) => p.match.test(pathname));
      if (sub) crumbs.push(...sub.trail);

      return crumbs;
    }
  }

  return [];
}
