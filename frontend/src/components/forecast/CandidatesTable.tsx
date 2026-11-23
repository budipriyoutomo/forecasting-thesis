"use client";

import { ChevronRight } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { MetricHeader } from "@/components/forecast/MetricHeader";
import { MetricValue } from "@/components/forecast/MetricValue";
import { metricColumns } from "@/lib/metrics";
import type { ForecastCandidate } from "@/types/forecast";
import type { DisplayMetric } from "@/types/forecastSettings";

// Perbandingan metode — urutan dari backend (tidak diurutkan ulang di sini), kolom metrik sesuai
// checkbox Pengaturan Forecast. 23 Nov 2026: run baru membawa peringkat (`rank`, 1 = metode
// terbaik pilihan sistem, prioritas MAD → MAPE → MFE) → kolom "Peringkat" + badge "terbaik"; run Fase 11.15 tanpa rank
// tampil seperti dulu. Planner tetap bisa mengganti metode lewat tombol "Pilih".
// Pengujian peramalan: kolom MAD, MFE, MAPE sesuai checkbox (keputusan user 21 Nov 2026);
// tiap header punya tooltip definisi; sel MAPE membawa label skala Lewis (bukan peringkat).
export function CandidatesTable({
  candidates,
  selectedMethod,
  displayMetrics,
  onSelect,
  defaultOpen,
}: {
  candidates: ForecastCandidate[];
  selectedMethod: string | null;
  displayMetrics: DisplayMetric[];
  onSelect?: (method: string) => void;
  /** Default: terbuka bila metode belum dipilih. */
  defaultOpen?: boolean;
}) {
  // Mode manual: satu kandidat & tak ada yang bisa dipilih — tabel jadi misleading.
  if (candidates.length < 2 && !onSelect) return null;
  const columns = metricColumns(displayMetrics);
  const ranked = candidates.some((c) => typeof c.rank === "number");

  return (
    <Collapsible className="rounded-lg border" defaultOpen={defaultOpen ?? !selectedMethod}>
      <CollapsibleTrigger className="group flex w-full items-center gap-2 p-3 text-sm font-medium hover:bg-muted/50">
        <ChevronRight className="size-4 transition-transform group-data-[state=open]:rotate-90" />
        Perbandingan metode ({candidates.length} metode)
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="overflow-x-auto border-t">
          <Table>
            <TableHeader>
              <TableRow>
                {ranked && <TableHead>Peringkat</TableHead>}
                <TableHead>Metode</TableHead>
                {columns.map((m) => (
                  <TableHead key={m}>
                    <MetricHeader metric={m} />
                  </TableHead>
                ))}
                {onSelect && <TableHead className="sr-only">Aksi</TableHead>}
              </TableRow>
            </TableHeader>
            <TableBody>
              {candidates.map((c) => {
                const used = c.method === selectedMethod;
                const selectable = Boolean(onSelect && c.forecast && c.forecast.length > 0);
                return (
                  <TableRow key={c.method}>
                    {ranked && <TableCell className="tabular-nums">{c.rank ?? "—"}</TableCell>}
                    <TableCell>
                      <span className={used ? "font-semibold" : undefined}>{c.method}</span>
                      {c.rank === 1 && (
                        <Badge variant="success" className="ml-2">
                          terbaik
                        </Badge>
                      )}
                      {used && (
                        <Badge variant="secondary" className="ml-2">
                          dipakai
                        </Badge>
                      )}
                    </TableCell>
                    {columns.map((m) => (
                      <TableCell key={m}>
                        <MetricValue metric={m} value={c[m]} />
                      </TableCell>
                    ))}
                    {onSelect && (
                      <TableCell className="text-right">
                        {selectable && !used && (
                          <Button
                            size="sm"
                            variant="outline"
                            aria-label={`Pilih ${c.method}`}
                            onClick={() => onSelect(c.method)}
                          >
                            Pilih
                          </Button>
                        )}
                      </TableCell>
                    )}
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
