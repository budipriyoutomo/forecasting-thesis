"use client";

import { Trophy } from "lucide-react";

import { MetricHeader } from "@/components/forecast/MetricHeader";
import { MetricValue } from "@/components/forecast/MetricValue";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { METRIC_INFO, metricColumns } from "@/lib/metrics";
import { methodLabel } from "@/lib/methods";
import type { ForecastResult, SelectionAnalysis } from "@/types/forecast";
import type { DisplayMetric } from "@/types/forecastSettings";

/** Analisis global run (sama di tiap hasil auto); null = run lama / manual / semua gagal. */
export function globalAnalysis(results: ForecastResult[]): SelectionAnalysis | null {
  return results.find((r) => r.selection_analysis?.scope === "global")?.selection_analysis ?? null;
}

// 23 Nov 2026 — metode terbaik dipilih SEKALI untuk seluruh produk dari RATA-RATA pengujian
// (MAD → MAPE → |MFE|). Angka & teks alasan dari backend (`selection.select_global_method`);
// komponen ini hanya menampilkan (AGENTS #20).
export function GlobalSelectionPanel({
  analysis,
  displayMetrics,
}: {
  analysis: SelectionAnalysis;
  displayMetrics?: DisplayMetric[];
}) {
  const columns = metricColumns(displayMetrics);
  const label = (m: string) => METRIC_INFO[m as keyof typeof METRIC_INFO]?.label ?? m.toUpperCase();
  const priority = analysis.criteria.map((m, i) => `${i + 1}) ${label(m)}`).join(", ");

  return (
    <section className="rounded-lg border-l-4 border-success bg-muted/50 p-4 text-sm">
      <p className="flex items-center gap-2 font-medium">
        <Trophy className="size-4" aria-hidden />
        Metode terbaik untuk seluruh produk: {methodLabel(analysis.best_method)}
      </p>
      <p className="mt-1 text-xs text-muted-foreground">
        Dinilai dari rata-rata pengujian {analysis.n_products ?? 1} produk · urutan prioritas: {priority}
        {analysis.decided_by && <> · penentu: {label(analysis.decided_by)}</>}.
      </p>
      <p className="mt-2 text-muted-foreground">{analysis.summary}</p>
      {analysis.reasons.length > 0 && (
        <ul className="mt-2 list-disc space-y-1 pl-5 text-muted-foreground">
          {analysis.reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      )}
      <div className="mt-3 overflow-x-auto rounded-md border bg-background">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Peringkat</TableHead>
              <TableHead>Metode</TableHead>
              {columns.map((m) => (
                <TableHead key={m}>
                  <MetricHeader metric={m} label={`Rata-rata ${METRIC_INFO[m].label}`} />
                </TableHead>
              ))}
              <TableHead>Produk</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {analysis.ranking.map((row) => (
              <TableRow key={row.method}>
                <TableCell className="tabular-nums">{row.rank}</TableCell>
                <TableCell>
                  <span className="flex items-center gap-2">
                    {methodLabel(row.method)}
                    {row.rank === 1 && <Badge variant="success">terbaik</Badge>}
                  </span>
                </TableCell>
                {columns.map((m) => (
                  <TableCell key={m}>
                    <MetricValue metric={m} value={row[m]} />
                  </TableCell>
                ))}
                <TableCell className="tabular-nums">{row.n_products ?? "—"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </section>
  );
}
