"use client";

import { StatTile } from "@/components/dashboard/StatTile";
import { formatMoney } from "@/lib/format";
import type { CostSummary } from "@/types/metrics";

// Ringkasan total biaya persediaan (Fase 7): TIC ForecastIQ vs TIC existing +
// % penghematan. Penghematan negatif → tone urgent (ForecastIQ lebih mahal).
export function CostSummaryCard({ summary }: { summary: CostSummary }) {
  const savings = Number(summary.savings_pct);

  return (
    <section className="flex flex-col gap-2">
      <h3 className="text-sm font-medium text-muted-foreground">Total Biaya Persediaan</h3>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <StatTile label="TIC ForecastIQ" value={formatMoney(summary.total_inventory_cost)} />
        <StatTile
          label="TIC Existing (planning)"
          value={formatMoney(summary.baseline_inventory_cost)}
        />
        <StatTile
          label="Penghematan"
          value={`${savings.toFixed(1)}%`}
          tone={savings >= 0 ? "default" : "urgent"}
          hint={savings >= 0 ? "Lebih murah dari planning" : "Lebih mahal dari planning"}
        />
      </div>
    </section>
  );
}
