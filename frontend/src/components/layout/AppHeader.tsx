"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { SidebarNav } from "@/components/layout/SidebarNav";
import { Button } from "@/components/ui/button";
import { logout, useMe } from "@/hooks/useAuth";

// Header global area dashboard: brand, navigasi, identitas user, dan logout.
// Logout dipusatkan di sini supaya tidak diduplikasi tiap halaman.
export function AppHeader() {
  const router = useRouter();
  const { data: user } = useMe();

  const onLogout = () => {
    logout();
    router.push("/login");
  };

  return (
    <header className="sticky top-0 z-10 border-b bg-background">
      <div className="container flex h-14 items-center gap-6">
        <Link href="/dashboard" className="text-base font-semibold">
          ForecastIQ
        </Link>
        <SidebarNav className="hidden md:flex" />
        <div className="ml-auto flex items-center gap-3">
          {user && (
            <span className="hidden text-sm text-muted-foreground sm:inline">
              {user.name} — {user.role}
            </span>
          )}
          <Button variant="outline" size="sm" onClick={onLogout}>
            Keluar
          </Button>
        </div>
      </div>
      <SidebarNav className="container flex-wrap pb-2 md:hidden" />
    </header>
  );
}
