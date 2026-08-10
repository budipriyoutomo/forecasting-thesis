"use client";

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

  const ranked = [...candidates].sort((a, b) => rankValue(a, rankingMetric) - rankValue(b, rankingMetric));

  return (
    <details className="mt-1 rounded-md border bg-muted/30 p-2">
      <summary className="cursor-pointer text-sm font-medium">
        Dasar perbandingan ({candidates.length} metode diuji)
      </summary>
      <div className="mt-2 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-muted-foreground">
              <th className="py-1 pr-4 font-medium">Metode</th>
              <th className="py-1 pr-4 font-medium">{METRIC_LABEL.mape}</th>
              <th className="py-1 pr-4 font-medium">{METRIC_LABEL.mad}</th>
              <th className="py-1 pr-4 font-medium">{METRIC_LABEL.mfe}</th>
              <th className="py-1 pr-4 font-medium">{METRIC_LABEL.mse}</th>
              <th className="py-1 font-medium">{METRIC_LABEL.mase}</th>
            </tr>
          </thead>
          <tbody>
            {ranked.map((c) => (
              <tr key={c.method} className="border-b last:border-0">
                <td className="py-1 pr-4">
                  <span className={c.method === winner ? "font-semibold" : undefined}>{c.method}</span>
                  {c.method === winner && (
                    <span className="ml-2 rounded bg-primary/10 px-1.5 py-0.5 text-xs">terpilih</span>
                  )}
                </td>
                <td className="py-1 pr-4">{fmt(c.mape, "mape")}</td>
                <td className="py-1 pr-4">{fmt(c.mad, "mad")}</td>
                <td className="py-1 pr-4">{fmt(c.mfe, "mfe")}</td>
                <td className="py-1 pr-4">{fmt(c.mse, "mse")}</td>
                <td className="py-1">{fmt(c.mase, "mase")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}
