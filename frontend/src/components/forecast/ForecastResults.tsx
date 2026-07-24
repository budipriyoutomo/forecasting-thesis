"use client";

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
      <p className="text-sm">
        Run <span className="font-medium">{run.status}</span> · {run.n_completed} berhasil ·{" "}
        {run.n_failed} gagal dari {run.n_materials} material.
      </p>

      <div className="flex flex-col gap-3">
        {results.map((r) => (
          <div key={r.material_id} className="rounded-lg border p-4">
            <div className="flex items-center justify-between">
              <span className="font-medium">{r.material_id}</span>
              <span className="text-sm text-muted-foreground">
                {STATUS_LABEL[r.status] ?? r.status}
              </span>
            </div>

            {r.status === "COMPLETED" && (
              <div className="mt-2 flex flex-col gap-1 text-sm">
                <p>
                  Metode: <span className="font-medium">{r.method_used}</span> (
                  {r.selection_mode === "manual" ? "dipilih manual" : "dipilih otomatis"})
                  {r.demand_class && <> · pola {r.demand_class}</>}
                  {r.mase != null && <> · MASE {r.mase.toFixed(2)}</>}
                </p>
                {r.explanation && <p className="text-muted-foreground">{r.explanation}</p>}
                <p className="text-muted-foreground">{r.forecast.length} titik forecast.</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
