"use client";

import { StatTile } from "@/components/dashboard/StatTile";
import { formatMoney } from "@/lib/format";
import type { CostSummary } from "@/types/metrics";

// Ringkasan total biaya persediaan (Fase 7): TIC ForecastIQ vs TIC existing +
// % penghematan. Penghematan negatif → tone urgent (ForecastIQ lebih mahal).
// Fase 10: sumber S & H (template aktif / default sistem) dan biaya pembelian
// material sebagai informasi terpisah — tidak dijumlahkan ke TIC.
export function CostSummaryCard({ summary }: { summary: CostSummary }) {
  const savings = Number(summary.savings_pct);
  const missing = summary.n_materials_without_price ?? 0;

  return (
    <section className="flex flex-col gap-2">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-sm font-medium text-muted-foreground">Total Biaya Persediaan</h3>
        {summary.cost_source && (
          <p className="text-xs text-muted-foreground">
            {summary.cost_source === "template"
              ? `Biaya pesan & simpan dari template biaya: ${summary.cost_template_name}`
              : "Biaya pesan & simpan dari biaya default sistem (belum ada template aktif)"}
          </p>
        )}
      </div>
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
      {summary.purchase_cost !== undefined && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <StatTile
            label="Biaya pembelian material"
            value={formatMoney(summary.purchase_cost)}
            hint={
              missing > 0
                ? `Informasi, tidak termasuk TIC — ${missing} material belum punya harga`
                : "Informasi, tidak termasuk TIC"
            }
          />
        </div>
      )}
    </section>
  );
}
