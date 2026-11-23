"use client";

import { AlertTriangle, Coins, ShieldCheck, Target } from "lucide-react";
import Link from "next/link";

import { EmptyState } from "@/components/common/EmptyState";
import { PageHeader } from "@/components/common/PageHeader";
import { ReorderStatusBar } from "@/components/dashboard/ReorderStatusBar";
import { StatTile } from "@/components/dashboard/StatTile";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useDashboardSummary } from "@/hooks/useDashboard";
import { formatDateTime, formatMoney, formatNumber, formatPercent } from "@/lib/format";
import { METRIC_INFO, bestAccuracyMetric, formatMetric } from "@/lib/metrics";
import { mapeLabel } from "@/lib/mape";
import { runStatus } from "@/lib/status";
import type { DashboardMetricScope, DashboardSummary } from "@/types/dashboard";

const SCOPE_LABEL: Record<string, string> = { baseline: "Existing (baseline)", forecastiq: "ForecastIQ" };
const ratio = (v: number | null) => (v == null ? "—" : formatPercent(v * 100, 1));
const turns = (v: number | null) => (v == null ? "—" : `${formatNumber(v)}×`);
const MAX_OVER = 5;

// Tile akurasi (keputusan user 21 Nov 2026): rata-rata MAD, MFE, MAPE run terakhir — tampilkan
// yang error-nya paling kecil (paling mendekati kebenaran) + namanya; dua lainnya di hint.
function accuracy(run: DashboardSummary["latest_run"]) {
  if (!run) return { label: "Akurasi forecast", value: "—", hint: "Belum ada run" };
  const avg = { mad: run.avg_mad, mfe: run.avg_mfe, mape: run.avg_mape };
  const best = bestAccuracyMetric(avg);
  if (!best) return { label: "Akurasi forecast", value: "—", hint: "Belum ada metrik pengujian" };
  const others = (["mad", "mfe", "mape"] as const)
    .filter((k) => k !== best.key && avg[k] != null)
    .map((k) => `${METRIC_INFO[k].label} ${formatMetric(avg[k], k)}`);
  const lewis = best.key === "mape" ? ` (${mapeLabel(best.value)})` : "";
  return {
    label: `Akurasi forecast (${METRIC_INFO[best.key].label} rata-rata)`,
    value: formatMetric(best.value, best.key),
    hint: [`error rata-rata terkecil${lewis}`, ...others].join(" · "),
  };
}

function costHint(run: NonNullable<DashboardSummary["latest_run"]>): string | undefined {
  if (run.savings_pct == null || run.total_inventory_cost_baseline == null) return undefined;
  const verb = run.savings_pct >= 0 ? "hemat" : "lebih mahal";
  return `${verb} ${formatPercent(Math.abs(run.savings_pct), 1)} vs baseline ${formatMoney(run.total_inventory_cost_baseline)}`;
}

// CR v3.6 §3 — tata letak dashboard: KPI (akurasi MAD/MFE/MAPE · reorder · α · TIC) → run terakhir → status
// reorder → kinerja inventory → kapasitas gudang → butuh perhatian. Setiap field
// DashboardSummary punya tempat; tidak ada angka ganda; tiap kartu punya empty state.
export default function DashboardPage() {
  const { data: summary, isPending, isError } = useDashboardSummary();
  const run = summary?.latest_run ?? null;
  const runHref = run ? `/forecast/runs/${run.run_id}` : undefined;
  const reorderHref = run ? `/forecast/runs/${run.run_id}?step=reorder` : undefined;
  const alpha: DashboardMetricScope | undefined = summary?.inventory_metrics?.forecastiq;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Dashboard"
        description="Ringkasan run forecast terakhir: akurasi, reorder, kinerja inventory, dan kapasitas gudang."
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
            <StatTile {...accuracy(run)} icon={Target} />
            <StatTile
              label="Material perlu reorder"
              value={summary.reorder_status_counts.urgent}
              tone={summary.reorder_status_counts.urgent > 0 ? "urgent" : "default"}
              hint={`dari ${summary.n_materials} material`}
              icon={AlertTriangle}
              href={reorderHref}
            />
            <StatTile
              label="Service level (α)"
              value={ratio(alpha?.service_level ?? null)}
              hint={
                summary.inventory_metrics?.baseline?.service_level != null
                  ? `baseline ${ratio(summary.inventory_metrics.baseline.service_level)}`
                  : alpha
                    ? undefined
                    : "Jalankan perencanaan untuk menghitung"
              }
              icon={ShieldCheck}
            />
            <StatTile
              label="Total biaya persediaan (TIC)"
              value={run ? formatMoney(run.total_inventory_cost) : "—"}
              hint={run ? costHint(run) : undefined}
              icon={Coins}
            />
          </div>

          <Card>
            <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-2 space-y-0">
              <div className="flex flex-col gap-1.5">
                <CardTitle className="text-lg">Run forecast terakhir</CardTitle>
                <CardDescription>
                  {run
                    ? `${formatDateTime(run.created_at ?? null)}${run.created_by ? ` · oleh ${run.created_by}` : ""}`
                    : "Belum ada run. Mulai dari menu Forecast."}
                </CardDescription>
              </div>
              {runHref && (
                <Button asChild variant="outline" size="sm">
                  <Link href={runHref}>Lihat detail run</Link>
                </Button>
              )}
            </CardHeader>
            {run && (
              <CardContent className="flex flex-col gap-3">
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <Badge variant={runStatus(run.status).variant}>{runStatus(run.status).label}</Badge>
                  <span>
                    {run.n_completed} berhasil · {run.n_failed} gagal dari {run.n_products} produk
                    {(run.n_pending_selection ?? 0) > 0 && ` · ${run.n_pending_selection} menunggu pemilihan metode`}
                  </span>
                </div>
                {(run.n_pending_selection ?? 0) > 0 && (
                  <div>
                    <Button asChild size="sm">
                      <Link href={`${runHref}?step=select`}>Pilih metode untuk {run.n_pending_selection} produk</Link>
                    </Button>
                  </div>
                )}
              </CardContent>
            )}
          </Card>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Status reorder</CardTitle>
                <CardDescription>{summary.n_materials} material terdaftar.</CardDescription>
              </CardHeader>
              <CardContent>
                <ReorderStatusBar counts={summary.reorder_status_counts} href={reorderHref} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Kinerja inventory</CardTitle>
                <CardDescription>Existing (planning perusahaan) vs ForecastIQ.</CardDescription>
              </CardHeader>
              <CardContent>
                {summary.inventory_metrics ? (
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Scope</TableHead>
                          <TableHead className="text-right">Service level (α)</TableHead>
                          <TableHead className="text-right">Fill rate (β)</TableHead>
                          <TableHead className="text-right">Stock-out rate</TableHead>
                          <TableHead className="text-right">Turnover</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {Object.entries(summary.inventory_metrics).map(([scope, m]) => (
                          <TableRow key={scope}>
                            <TableCell className="font-medium">{SCOPE_LABEL[scope] ?? scope}</TableCell>
                            <TableCell className="text-right tabular-nums">{ratio(m.service_level)}</TableCell>
                            <TableCell className="text-right tabular-nums">{ratio(m.fill_rate)}</TableCell>
                            <TableCell className="text-right tabular-nums">{ratio(m.stock_out_rate)}</TableCell>
                            <TableCell className="text-right tabular-nums">{turns(m.inventory_turnover)}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                ) : (
                  <EmptyState message="Jalankan perencanaan untuk melihat kinerja inventory." />
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Kapasitas gudang produk jadi</CardTitle>
                <CardDescription>
                  {summary.warehouse
                    ? `${summary.warehouse.n_products_over} dari ${summary.warehouse.n_products_checked} produk melebihi kapasitasnya.`
                    : "Belum dicek untuk run terakhir."}
                </CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                {summary.warehouse ? (
                  <>
                    <Badge
                      className="w-fit"
                      variant={summary.warehouse.is_within_capacity ? "success" : "destructive"}
                    >
                      {summary.warehouse.is_within_capacity ? "Muat di gudang" : "Melebihi kapasitas gudang"}
                    </Badge>
                    {(summary.warehouse.products_over ?? []).length > 0 && (
                      <ul className="flex flex-col divide-y rounded-lg border text-sm">
                        {(summary.warehouse.products_over ?? []).slice(0, MAX_OVER).map((p) => (
                          <li key={p.product_id} className="flex items-center justify-between gap-2 p-2">
                            <span>
                              <span className="font-medium">{p.code ?? p.product_id}</span>
                              {p.name && ` — ${p.name}`}
                            </span>
                            <span className="tabular-nums text-destructive">+{formatNumber(p.excess_qty)}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                    {summary.warehouse.n_products_over > MAX_OVER && reorderHref && (
                      <Link href={reorderHref} className="text-sm font-medium underline underline-offset-4">
                        Lihat semua ({summary.warehouse.n_products_over})
                      </Link>
                    )}
                  </>
                ) : (
                  <EmptyState message="Buka langkah Reorder & gudang di detail run untuk mengecek kapasitas." />
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Butuh perhatian</CardTitle>
                <CardDescription>Hal yang perlu ditindaklanjuti dari run terakhir.</CardDescription>
              </CardHeader>
              <CardContent>
                <AttentionList summary={summary} runHref={runHref} />
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}

function AttentionList({ summary, runHref }: { summary: DashboardSummary; runHref?: string }) {
  const a = summary.attention;
  const items = [
    { n: summary.latest_run?.n_pending_selection ?? 0, text: "produk menunggu pemilihan metode", href: runHref && `${runHref}?step=select` },
    { n: a?.n_failed_products ?? 0, text: "produk gagal di-forecast", href: runHref && `${runHref}?step=forecast` },
    { n: a?.n_missing_cost_data ?? 0, text: "material tanpa harga / holding rate (EOQ dinamis)", href: "/materials" },
    { n: a?.n_shortage_periods ?? 0, text: "periode kekurangan stok di proyeksi", href: runHref && `${runHref}?step=planning` },
    { n: summary.n_recent_overrides, text: "override planner terbaru", href: runHref && `${runHref}?step=reorder` },
  ].filter((i) => i.n > 0);

  if (items.length === 0) return <EmptyState message="Tidak ada yang perlu ditindaklanjuti." />;
  return (
    <ul className="flex flex-col divide-y rounded-lg border text-sm">
      {items.map((i) => (
        <li key={i.text} className="flex items-center justify-between gap-2 p-2">
          <span>
            <span className="font-semibold tabular-nums">{i.n}</span> {i.text}
          </span>
          {i.href && (
            <Link href={i.href} className="shrink-0 text-sm font-medium underline underline-offset-4">
              Buka
            </Link>
          )}
        </li>
      ))}
    </ul>
  );
}
