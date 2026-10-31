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
import type { RankingMetric } from "@/types/forecastSettings";

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

// Kolom peringkat (Fase 11.2a, Keputusan #6) — dihitung backend, tampil berdampingan.
const RANK_COLUMNS: { metric: RankingMetric; key: "rank_mad" | "rank_mfe" | "rank_mape"; label: string }[] = [
  { metric: "mad", key: "rank_mad", label: "MAD" },
  { metric: "mfe_abs", key: "rank_mfe", label: "|MFE|" },
  { metric: "mape", key: "rank_mape", label: "MAPE" },
];

function fmtRank(rank: number | null | undefined): string {
  return rank == null ? "—" : `#${rank}`;
}

function fmt(value: number | null, key: string): string {
  if (value === null || Number.isNaN(value)) return "—";
  return key === "mape" ? `${value.toFixed(2)}%` : value.toFixed(2);
}

// Dasar perbandingan Comparative Selection: seluruh metode yang diuji + metriknya,
// diurutkan dari yang terbaik menurut metrik ranking. Planner bisa menilai apakah
// selisih akurasinya berarti — bukan sekadar menerima "sistem memilih X".
// 3 kolom peringkat (MAD, |MFE|, MAPE) jadi acuan; kolom metrik aktif ditandai.
export function CandidatesTable({
  candidates,
  winner,
  rankingMetric = "mad",
}: {
  candidates: ForecastCandidate[];
  winner: string | null;
  rankingMetric?: RankingMetric | null;
}) {
  const metric: RankingMetric = rankingMetric ?? "mad";
  // Satu kandidat = tidak ada yang dibandingkan (mode manual) — tabel jadi misleading.
  if (candidates.length < 2) return null;

  const ranked = [...candidates].sort(
    (a, b) => rankValue(a, metric) - rankValue(b, metric),
  );
  const activeLabel = RANK_COLUMNS.find((c) => c.metric === metric)?.label;

  return (
    <Collapsible className="rounded-lg border">
      <CollapsibleTrigger className="group flex w-full items-center gap-2 p-3 text-sm font-medium hover:bg-muted/50">
        <ChevronRight className="size-4 transition-transform group-data-[state=open]:rotate-90" />
        Dasar perbandingan ({candidates.length} metode diuji)
      </CollapsibleTrigger>
      <CollapsibleContent>
        {/* Run sebelum Fase 11.2a tak mencatat metriknya — jangan klaim metrik yang belum tentu dipakai. */}
        {rankingMetric && (
          <p className="border-t px-3 py-2 text-xs text-muted-foreground">
            Pemenang ditentukan oleh {activeLabel} (Pengaturan Forecast). Peringkat lain sebagai acuan.
          </p>
        )}
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
                {RANK_COLUMNS.map((col) => (
                  <TableHead
                    key={col.key}
                    aria-sort={col.metric === metric ? "ascending" : undefined}
                    className={col.metric === metric ? "font-semibold text-foreground" : undefined}
                  >
                    Rank {col.label}
                  </TableHead>
                ))}
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
                  {RANK_COLUMNS.map((col) => (
                    <TableCell
                      key={col.key}
                      className={
                        col.metric === metric ? "tabular-nums font-semibold" : "tabular-nums"
                      }
                    >
                      {fmtRank(c[col.key])}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
