"use client";

import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { logout, useMe } from "@/hooks/useAuth";

export default function DashboardPage() {
  const router = useRouter();
  const { data: user, isPending, isError } = useMe();

  const onLogout = () => {
    logout();
    router.push("/login");
  };

  return (
    <main className="container flex min-h-screen flex-col gap-4 py-16">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <Button variant="outline" size="sm" onClick={onLogout}>
          Keluar
        </Button>
      </div>

      {isPending && <p className="text-sm text-muted-foreground">Memuat profil…</p>}
      {isError && <p className="text-sm text-destructive">Gagal memuat profil. Silakan login ulang.</p>}
      {user && (
        <p className="text-sm">
          Halo, <span className="font-medium">{user.name}</span> — peran{" "}
          <span className="font-medium">{user.role}</span>.
        </p>
      )}
    </main>
  );
}
