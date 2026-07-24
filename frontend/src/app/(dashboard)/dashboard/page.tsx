"use client";

import { useRouter } from "next/navigation";

import { StatTile } from "@/components/dashboard/StatTile";
import { Button } from "@/components/ui/button";
import { useMe, logout } from "@/hooks/useAuth";
import { useDashboardSummary } from "@/hooks/useDashboard";

export default function DashboardPage() {
  const router = useRouter();
  const { data: user } = useMe();
  const { data: summary, isPending, isError } = useDashboardSummary();

  const onLogout = () => {
    logout();
    router.push("/login");
  };

  return (
    <main className="container flex min-h-screen flex-col gap-6 py-16">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          {user && (
            <p className="text-sm text-muted-foreground">
              {user.name} — {user.role}
            </p>
          )}
        </div>
        <Button variant="outline" size="sm" onClick={onLogout}>
          Keluar
        </Button>
      </div>

      {isPending && <p className="text-sm text-muted-foreground">Memuat ringkasan…</p>}
      {isError && <p className="text-sm text-destructive">Gagal memuat ringkasan dashboard.</p>}

      {summary && (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <StatTile label="Total material" value={summary.n_materials} />
            <StatTile label="Perlu reorder" value={summary.reorder_status_counts.urgent} tone="urgent" />
            <StatTile
              label="Akurasi (MASE rata-rata)"
              value={summary.latest_run?.avg_mase ?? "—"}
            />
            <StatTile label="Override terbaru" value={summary.n_recent_overrides} />
          </div>

          <section className="flex flex-col gap-2">
            <h2 className="text-lg font-medium">Run forecast terakhir</h2>
            {summary.latest_run ? (
              <p className="text-sm">
                Status <span className="font-medium">{summary.latest_run.status}</span> ·{" "}
                {summary.latest_run.n_completed} berhasil · {summary.latest_run.n_failed} gagal dari{" "}
                {summary.latest_run.n_materials} material.
              </p>
            ) : (
              <p className="text-sm text-muted-foreground">
                Belum ada run. Mulai dari menu Forecast.
              </p>
            )}
          </section>

          <div className="grid grid-cols-3 gap-3">
            <StatTile label="Urgent" value={summary.reorder_status_counts.urgent} tone="urgent" />
            <StatTile label="Aman" value={summary.reorder_status_counts.safe} />
            <StatTile label="Overstock" value={summary.reorder_status_counts.overstock} />
          </div>
        </>
      )}
    </main>
  );
}
