"use client";

import { StatTile } from "@/components/dashboard/StatTile";
import type { CostSummary } from "@/types/metrics";

function fmt(value: string): string {
  return Number(value).toLocaleString("id-ID", { maximumFractionDigits: 2 });
}

// Ringkasan total biaya persediaan (Fase 7): TIC ForecastIQ vs TIC existing +
// % penghematan. Penghematan negatif → tone urgent (ForecastIQ lebih mahal).
export function CostSummaryCard({ summary }: { summary: CostSummary }) {
  const savings = Number(summary.savings_pct);
  return (
    <section>
      <h3 className="mb-2 text-sm font-medium text-muted-foreground">Total Biaya Persediaan</h3>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <StatTile label="TIC ForecastIQ" value={fmt(summary.total_inventory_cost)} />
        <StatTile label="TIC Existing (planning)" value={fmt(summary.baseline_inventory_cost)} />
        <StatTile
          label="Penghematan"
          value={`${savings.toFixed(1)}%`}
          tone={savings >= 0 ? "default" : "urgent"}
        />
      </div>
    </section>
  );
}
