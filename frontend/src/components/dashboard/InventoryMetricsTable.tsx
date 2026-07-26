"use client";

import type { InventoryMetric } from "@/types/metrics";

const SCOPE_LABEL: Record<string, string> = {
  baseline: "Existing (baseline)",
  forecastiq: "ForecastIQ",
};

function pct(value: string): string {
  return `${(Number(value) * 100).toFixed(1)}%`;
}

function turns(value: string): string {
  return `${Number(value).toFixed(2)}×`;
}

// Evaluasi kinerja inventory per scope (Fase 7): baseline (actual vs planning)
// vs forecastiq (actual vs forecast ForecastIQ) — membuktikan perbaikan thesis.
export function InventoryMetricsTable({ metrics }: { metrics: InventoryMetric[] }) {
  if (metrics.length === 0) {
    return <p className="text-sm text-muted-foreground">Belum ada metrik inventory untuk run ini.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left text-muted-foreground">
            <th className="py-2 pr-4 font-medium">Scope</th>
            <th className="py-2 pr-4 font-medium">Service Level</th>
            <th className="py-2 pr-4 font-medium">Fill Rate</th>
            <th className="py-2 pr-4 font-medium">Stock Out</th>
            <th className="py-2 font-medium">Turnover</th>
          </tr>
        </thead>
        <tbody>
          {metrics.map((m) => (
            <tr key={`${m.scope}-${m.target_id}`} className="border-b last:border-0">
              <td className="py-2 pr-4 font-medium">{SCOPE_LABEL[m.scope] ?? m.scope}</td>
              <td className="py-2 pr-4">{pct(m.service_level)}</td>
              <td className="py-2 pr-4">{pct(m.fill_rate)}</td>
              <td className="py-2 pr-4">{pct(m.stock_out_rate)}</td>
              <td className="py-2">{turns(m.inventory_turnover)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
