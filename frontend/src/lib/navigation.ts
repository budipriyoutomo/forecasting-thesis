import {
  Boxes,
  LayoutDashboard,
  LineChart,
  Network,
  Package,
  Warehouse,
  type LucideIcon,
} from "lucide-react";

// Sumber tunggal struktur navigasi: dipakai sidebar sekaligus breadcrumb, supaya
// keduanya tidak bisa saling tidak sinkron. Urutan grup mengikuti alur kerja PPIC —
// master data (produk → material → BOM) dulu, baru operasional (forecast → gudang).

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
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
    ],
  },
  {
    label: "Operasional",
    items: [
      { href: "/forecast/new", label: "Forecast", icon: LineChart },
      { href: "/warehouse", label: "Gudang", icon: Warehouse },
    ],
  },
];

export function isActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

// Label untuk segmen di bawah menu — halaman yang tidak punya entri sidebar sendiri.
const SUB_PAGE_LABELS: Record<string, string> = {
  "/forecast/new/config": "Konfigurasi",
};

export interface Crumb {
  label: string;
  /** Tanpa href berarti jejak tidak bisa diklik: label grup, atau halaman saat ini. */
  href?: string;
}

export function breadcrumbsFor(pathname: string): Crumb[] {
  for (const group of NAV_GROUPS) {
    for (const item of group.items) {
      if (!isActive(pathname, item.href)) continue;

      const crumbs: Crumb[] = [];
      // Grup "Utama" hanya wadah, bukan tingkatan yang berarti bagi user.
      if (group.label !== "Utama") crumbs.push({ label: group.label });
      crumbs.push({ label: item.label, href: item.href });

      const sub = SUB_PAGE_LABELS[pathname];
      if (sub) crumbs.push({ label: sub });

      return crumbs;
    }
  }

  return [];
}
