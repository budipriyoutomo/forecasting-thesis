"use client";

import { AlertTriangle, Trophy } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { MetricHeader } from "@/components/forecast/MetricHeader";
import { MetricValue } from "@/components/forecast/MetricValue";
import { CopyTableButton } from "@/components/forecast/method-view/CopyTableButton";
import { NUM } from "@/components/forecast/method-view/MethodForecastMatrix";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { METRIC_INFO, formatMetric } from "@/lib/metrics";
import { methodLabel } from "@/lib/methods";
import { resultStatus } from "@/lib/status";
import type { MetricCriterion, ProductMethodRow, RunSelection } from "@/types/forecast";

// CR v3.7 §6 — analisis pemilihan metode terbaik level run. Peringkat, rata-rata & teks alasan
// = seleksi GLOBAL backend (`selection.select_global_method`), sama dengan metode yang dipakai
// run; komponen ini hanya menampilkan (AGENTS #20). D9 (varian dimenangkan) dihapus atas
// keputusan user 23 Nov 2026 — diganti tabel varian → metode dipakai.
export function BestMethodAnalysis({
  selection,
  criteria,
  productMethods,
  variantLabel,
}: {
  selection: RunSelection | null;
  criteria: MetricCriterion[];
  productMethods: ProductMethodRow[];
  variantLabel: (productId: string) => string;
}) {
  if (!selection) {
    return <EmptyState message="Belum ada metode yang berhasil diuji di run ini." />;
  }
  const label = (m: MetricCriterion) => METRIC_INFO[m].label;
  const priority = selection.criteria.map((m, i) => `${i + 1}) ${label(m)}`).join(", ");
  const decided = selection.decided_by ? ` · penentu: ${label(selection.decided_by)}` : "";
  const tsv = () => [
    ["Peringkat", "Metode", ...criteria.map((m) => `Avg ${label(m)}`), "Varian"],
    ...selection.ranking.map((r) => [
      String(r.rank),
      methodLabel(r.method),
      ...criteria.map((m) => formatMetric(r[m], m)),
      r.n_products != null ? String(r.n_products) : "—",
    ]),
  ];

  return (
    <div className="flex flex-col gap-4">
      <div className="-mb-2 flex justify-end">
        <CopyTableButton label="peringkat metode" rows={tsv} />
      </div>
      <div className="overflow-x-auto rounded-md border">
        <Table aria-label="Peringkat metode level run">
          <TableHeader>
            <TableRow>
              <TableHead>Peringkat</TableHead>
              <TableHead>Metode</TableHead>
              {criteria.map((m) => (
                <TableHead key={m} className="text-right">
                  <MetricHeader metric={m} label={`Avg ${label(m)}`} />
                </TableHead>
              ))}
              <TableHead className="text-right">Varian</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {selection.ranking.map((row) => {
              const best = row.method === selection.best_method;
              return (
                <TableRow key={row.method} data-best={best} className={best ? "bg-success/10 font-medium" : undefined}>
                  <TableCell className="tabular-nums">{row.rank}</TableCell>
                  <TableCell>
                    <span className="flex items-center gap-2">
                      {methodLabel(row.method)}
                      {best && <Badge variant="success">Terbaik</Badge>}
                    </span>
                  </TableCell>
                  {criteria.map((m) => (
                    <TableCell key={m} className={NUM}>
                      <MetricValue metric={m} value={row[m]} />
                    </TableCell>
                  ))}
                  <TableCell className={NUM}>{row.n_products ?? "—"}</TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      {selection.ranking_basis === "common" && (
        <Alert variant="warning">
          <AlertTriangle className="size-4" />
          <AlertDescription>
            Peringkat dihitung atas {selection.n_common} dari {selection.n_completed} varian yang berhasil, supaya
            rata-rata tiap metode sebanding.
            {selection.excluded_methods.length > 0 &&
              ` Tidak dibandingkan karena gagal di sebagian varian: ${selection.excluded_methods.map(methodLabel).join(", ")}.`}
          </AlertDescription>
        </Alert>
      )}

      <section className="rounded-lg border-l-4 border-success bg-muted/50 p-4 text-sm">
        <p className="flex items-center gap-2 font-medium">
          <Trophy className="size-4" aria-hidden />
          Kesimpulan: {methodLabel(selection.best_method)} adalah metode terbaik untuk seluruh varian
        </p>
        <p className="mt-2 text-muted-foreground">{selection.summary}</p>
        {selection.reasons.length > 0 && (
          <ul className="mt-2 list-disc space-y-1 pl-5 text-muted-foreground">
            {selection.reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        )}
        <p className="mt-2 text-xs text-muted-foreground">{`Urutan prioritas: ${priority}${decided}.`}</p>
      </section>

      <div className="overflow-x-auto rounded-md border">
        <Table aria-label="Metode per varian">
          <TableHeader>
            <TableRow>
              <TableHead>Varian</TableHead>
              <TableHead>Pilihan sistem</TableHead>
              <TableHead>Metode dipakai</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {productMethods.map((p) => (
              <TableRow key={p.product_id}>
                <TableCell className="font-medium">{variantLabel(p.product_id)}</TableCell>
                {p.status !== "COMPLETED" ? (
                  <TableCell colSpan={2}>
                    <Badge variant={resultStatus(p).variant}>{resultStatus(p).label}</Badge>
                  </TableCell>
                ) : (
                  <>
                    <TableCell>
                      {p.system_method ? methodLabel(p.system_method) : "—"}
                      {p.system_method && p.system_method !== selection.best_method && (
                        <span className="block text-xs text-muted-foreground">
                          terbaik varian ini ({methodLabel(selection.best_method)} gagal di varian ini)
                        </span>
                      )}
                    </TableCell>
                    <TableCell>
                      <span className="flex items-center gap-2">
                        {p.method_used ? methodLabel(p.method_used) : "—"}
                        {p.is_overridden && p.method_used !== p.system_method && (
                          <Badge variant="secondary">diganti planner</Badge>
                        )}
                      </span>
                    </TableCell>
                  </>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <p className="text-xs text-muted-foreground">
        Catatan metodologis: rata-rata MAD lintas varian mencampur skala volume yang berbeda, sehingga varian bervolume
        besar lebih berpengaruh. MAPE (bebas skala) lebih adil untuk membandingkan lintas varian; urutan prioritas
        pengujian tetap MAD → MAPE → MFE.
      </p>
    </div>
  );
}
