"use client";

import { ChevronRight } from "lucide-react";

import { Badge } from "@/components/ui/badge";
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

type RankingMetric = "mape" | "mad" | "mse" | "mfe_abs";

const METRIC_LABEL: Record<string, string> = {
  mape: "MAPE",
  mad: "MAD",
  mse: "MSE",
  mfe: "MFE",
  mase: "MASE",
};

function metricKey(metric: RankingMetric): keyof ForecastCandidate {
  return metric === "mfe_abs" ? "mfe" : metric;
}

function rankValue(candidate: ForecastCandidate, metric: RankingMetric): number {
  const value = candidate[metricKey(metric)];
  if (value === null || Number.isNaN(value)) return Number.POSITIVE_INFINITY;
  return metric === "mfe_abs" ? Math.abs(value as number) : (value as number);
}

function fmt(value: number | null, key: string): string {
  if (value === null || Number.isNaN(value)) return "—";
  return key === "mape" ? `${value.toFixed(2)}%` : value.toFixed(2);
}

// Dasar perbandingan Comparative Selection: seluruh metode yang diuji + metriknya,
// diurutkan dari yang terbaik menurut metrik ranking. Planner bisa menilai apakah
// selisih akurasinya berarti — bukan sekadar menerima "sistem memilih X".
export function CandidatesTable({
  candidates,
  winner,
  rankingMetric = "mape",
}: {
  candidates: ForecastCandidate[];
  winner: string | null;
  rankingMetric?: RankingMetric;
}) {
  // Satu kandidat = tidak ada yang dibandingkan (mode manual) — tabel jadi misleading.
  if (candidates.length < 2) return null;

  const ranked = [...candidates].sort(
    (a, b) => rankValue(a, rankingMetric) - rankValue(b, rankingMetric),
  );

  return (
    <Collapsible className="rounded-lg border">
      <CollapsibleTrigger className="group flex w-full items-center gap-2 p-3 text-sm font-medium hover:bg-muted/50">
        <ChevronRight className="size-4 transition-transform group-data-[state=open]:rotate-90" />
        Dasar perbandingan ({candidates.length} metode diuji)
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="overflow-x-auto border-t">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Metode</TableHead>
                <TableHead>{METRIC_LABEL.mape}</TableHead>
                <TableHead>{METRIC_LABEL.mad}</TableHead>
                <TableHead>{METRIC_LABEL.mfe}</TableHead>
                <TableHead>{METRIC_LABEL.mse}</TableHead>
                <TableHead>{METRIC_LABEL.mase}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {ranked.map((c) => (
                <TableRow key={c.method}>
                  <TableCell>
                    <span className={c.method === winner ? "font-semibold" : undefined}>
                      {c.method}
                    </span>
                    {c.method === winner && (
                      <Badge variant="secondary" className="ml-2">
                        terpilih
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell className="tabular-nums">{fmt(c.mape, "mape")}</TableCell>
                  <TableCell className="tabular-nums">{fmt(c.mad, "mad")}</TableCell>
                  <TableCell className="tabular-nums">{fmt(c.mfe, "mfe")}</TableCell>
                  <TableCell className="tabular-nums">{fmt(c.mse, "mse")}</TableCell>
                  <TableCell className="tabular-nums">{fmt(c.mase, "mase")}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
