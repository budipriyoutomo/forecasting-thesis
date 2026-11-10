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
import type { ForecastCandidate } from "@/types/forecast";
import type { DisplayMetric } from "@/types/forecastSettings";

const METRIC_LABEL: Record<DisplayMetric, string> = {
  mad: "MAD",
  mfe: "MFE",
  mse: "MSE",
  mape: "MAPE",
};

function fmt(value: number | null | undefined, key: DisplayMetric): string {
  if (value == null || Number.isNaN(value)) return "—";
  return key === "mape" ? `${value.toFixed(2)}%` : value.toFixed(2);
}

// Fase 11.15 — perbandingan metode TANPA pemenang & tanpa peringkat: semua metode tampil
// berdampingan (urutan dari backend, tidak diurutkan menurut metrik), kolom metrik sesuai
// checkbox Pengaturan Forecast. Planner memilih metode yang dipakai lewat tombol "Pilih".
export function CandidatesTable({
  candidates,
  selectedMethod,
  displayMetrics,
  onSelect,
}: {
  candidates: ForecastCandidate[];
  selectedMethod: string | null;
  displayMetrics: DisplayMetric[];
  onSelect?: (method: string) => void;
}) {
  // Mode manual: satu kandidat & tak ada yang bisa dipilih — tabel jadi misleading.
  if (candidates.length < 2 && !onSelect) return null;

  return (
    <Collapsible className="rounded-lg border" defaultOpen={!selectedMethod}>
      <CollapsibleTrigger className="group flex w-full items-center gap-2 p-3 text-sm font-medium hover:bg-muted/50">
        <ChevronRight className="size-4 transition-transform group-data-[state=open]:rotate-90" />
        Perbandingan metode ({candidates.length} metode)
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="overflow-x-auto border-t">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Metode</TableHead>
                {displayMetrics.map((m) => (
                  <TableHead key={m}>{METRIC_LABEL[m]}</TableHead>
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
                    <TableCell>
                      <span className={used ? "font-semibold" : undefined}>{c.method}</span>
                      {used && (
                        <Badge variant="secondary" className="ml-2">
                          dipakai
                        </Badge>
                      )}
                    </TableCell>
                    {displayMetrics.map((m) => (
                      <TableCell key={m} className="tabular-nums">
                        {fmt(c[m], m)}
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
