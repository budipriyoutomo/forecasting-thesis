"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

// Navigasi utama aplikasi. Urutannya mengikuti alur kerja PPIC:
// master data (produk → material → BOM) → forecast → kapasitas gudang.
const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/products", label: "Produk" },
  { href: "/materials", label: "Material" },
  { href: "/boms", label: "BOM" },
  { href: "/forecast/new", label: "Forecast" },
  { href: "/warehouse", label: "Gudang" },
] as const;

function isActive(pathname: string, href: string) {
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function SidebarNav({ className }: { className?: string }) {
  const pathname = usePathname();

  return (
    <nav className={cn("flex gap-1", className)}>
      {NAV_ITEMS.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          aria-current={isActive(pathname, item.href) ? "page" : undefined}
          className={cn(
            "rounded-md px-3 py-2 text-sm font-medium transition-colors",
            isActive(pathname, item.href)
              ? "bg-secondary text-secondary-foreground"
              : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
          )}
        >
          {item.label}
        </Link>
      ))}
    </nav>
  );
}
