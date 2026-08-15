"use client";

import { AlertTriangle, Boxes, PencilLine, Target } from "lucide-react";

import { PageHeader } from "@/components/common/PageHeader";
import { StatTile } from "@/components/dashboard/StatTile";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatMoney, formatNumber } from "@/lib/format";
import { useDashboardSummary } from "@/hooks/useDashboard";

export default function DashboardPage() {
  const { data: summary, isPending, isError } = useDashboardSummary();
  const run = summary?.latest_run;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Dashboard"
        description="Ringkasan run forecast terakhir, status reorder, dan kapasitas gudang."
      />

      {isPending && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4" role="status">
          <span className="sr-only">Memuat ringkasan…</span>
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      )}

      {isError && (
        <Alert variant="destructive">
          <AlertDescription>Gagal memuat ringkasan dashboard.</AlertDescription>
        </Alert>
      )}

      {summary && (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatTile label="Total material" value={summary.n_materials} icon={Boxes} />
            <StatTile
              label="Perlu reorder"
              value={summary.reorder_status_counts.urgent}
              tone={summary.reorder_status_counts.urgent > 0 ? "urgent" : "default"}
              icon={AlertTriangle}
            />
            <StatTile
              label="Akurasi (MASE rata-rata)"
              value={run?.avg_mase != null ? formatNumber(run.avg_mase) : "—"}
              hint={run?.avg_mape != null ? `MAPE ${formatNumber(run.avg_mape)}%` : undefined}
              icon={Target}
            />
            <StatTile
              label="Override terbaru"
              value={summary.n_recent_overrides}
              icon={PencilLine}
            />
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Run forecast terakhir</CardTitle>
              <CardDescription>
                {run
                  ? "Hasil run terakhir beserta biaya persediaan yang diusulkan."
                  : "Belum ada run. Mulai dari menu Forecast."}
              </CardDescription>
            </CardHeader>
            {run && (
              <CardContent className="flex flex-col gap-3">
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <Badge variant={run.status === "COMPLETED" ? "secondary" : "outline"}>
                    {run.status}
                  </Badge>
                  <span>
                    {run.n_completed} berhasil · {run.n_failed} gagal dari {run.n_materials} material
                  </span>
                </div>
                <p className="text-sm text-muted-foreground">
                  Total biaya persediaan: {formatMoney(run.total_inventory_cost)}
                </p>
              </CardContent>
            )}
          </Card>

          <section className="flex flex-col gap-3">
            <h2 className="text-lg font-medium">Status reorder</h2>
            <div className="grid gap-3 sm:grid-cols-3">
              <StatTile
                label="Segera reorder"
                value={summary.reorder_status_counts.urgent}
                tone={summary.reorder_status_counts.urgent > 0 ? "urgent" : "default"}
              />
              <StatTile label="Aman" value={summary.reorder_status_counts.safe} />
              <StatTile label="Kelebihan stok" value={summary.reorder_status_counts.overstock} />
            </div>
          </section>

          {summary.warehouse && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Kapasitas gudang</CardTitle>
                <CardDescription>
                  Butuh {formatNumber(summary.warehouse.total_pallet_required, 1)} palet dari{" "}
                  {formatNumber(summary.warehouse.total_pallet_capacity, 0)} tersedia.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Badge variant={summary.warehouse.is_within_capacity ? "secondary" : "destructive"}>
                  {summary.warehouse.is_within_capacity
                    ? "Muat di gudang"
                    : "Melebihi kapasitas gudang"}
                </Badge>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
