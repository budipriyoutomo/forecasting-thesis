"use client";

import { ExplanationBox } from "@/components/dashboard/ExplanationBox";
import { CandidatesTable } from "@/components/forecast/CandidatesTable";
import { ForecastChart } from "@/components/forecast/ForecastChart";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatNumber } from "@/lib/format";
import type { ForecastRunResponse } from "@/types/forecast";

const STATUS_LABEL: Record<string, string> = {
  COMPLETED: "Selesai",
  INSUFFICIENT_DATA: "Data kurang",
  MODEL_SELECTION_FAILED: "Gagal memilih model",
};

export function ForecastResults({ data }: { data: ForecastRunResponse }) {
  const { run, results } = data;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <Badge variant={run.status === "COMPLETED" ? "secondary" : "outline"}>{run.status}</Badge>
        <span>
          {run.n_completed} berhasil · {run.n_failed} gagal dari {run.n_products} produk.
        </span>
      </div>

      <div className="flex flex-col gap-4">
        {results.map((r) => (
          <Card key={r.product_id}>
            <CardHeader>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="flex flex-col gap-1">
                  <CardTitle className="text-base">{r.product_id}</CardTitle>
                  {r.status === "COMPLETED" && (
                    <CardDescription>
                      Metode <span className="font-medium">{r.method_used}</span> (
                      {r.selection_mode === "manual" ? "dipilih manual" : "dipilih otomatis"})
                      {r.mape != null && <> · MAPE {formatNumber(r.mape)}%</>}
                    </CardDescription>
                  )}
                </div>
                <Badge variant={r.status === "COMPLETED" ? "secondary" : "destructive"}>
                  {STATUS_LABEL[r.status] ?? r.status}
                </Badge>
              </div>
            </CardHeader>

            {r.status === "COMPLETED" && (
              <CardContent className="flex flex-col gap-4">
                <ExplanationBox explanation={r.explanation} />
                <CandidatesTable
                  candidates={r.candidates_evaluated ?? []}
                  winner={r.method_used}
                />
                <ForecastChart forecast={r.forecast} />
              </CardContent>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}
