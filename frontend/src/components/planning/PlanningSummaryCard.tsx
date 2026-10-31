"use client";

import { StatTile } from "@/components/dashboard/StatTile";
import type { PlanningSummary } from "@/types/planning";

// Ringkasan pipeline thesis (Fase 11.8): [2] MRP → [3] kapasitas gudang → [4] evaluasi.
export function PlanningSummaryCard({ summary }: { summary: PlanningSummary }) {
  const { reorder, projection, cost } = summary;
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      <StatTile
        label="[2] MRP & reorder"
        value={`${reorder.n_materials} material`}
        tone={reorder.n_urgent > 0 ? "urgent" : "default"}
        hint={
          reorder.n_missing_data > 0
            ? `${reorder.n_urgent} perlu segera dipesan · ${reorder.n_missing_data} material datanya belum lengkap (EOQ dinamis)`
            : `${reorder.n_urgent} perlu segera dipesan`
        }
      />
      <StatTile
        label="[3] Kapasitas gudang material"
        value={projection.n_over_capacity > 0 ? `${projection.n_over_capacity} periode melebihi kapasitas` : "Muat kapasitas"}
        tone={projection.n_over_capacity > 0 ? "urgent" : "default"}
        hint={
          projection.baseline_available
            ? `${projection.n_shortage_periods} periode kekurangan stok`
            : `${projection.n_shortage_periods} periode kekurangan stok · skenario existing tidak dihitung (planning horizon tidak tersedia)`
        }
      />
      <StatTile
        label="[4] Penghematan TIC"
        value={cost.savings_pct != null ? `${cost.savings_pct.toFixed(1)}%` : "—"}
        tone={(cost.savings_pct ?? 0) >= 0 ? "default" : "urgent"}
        hint={cost.eoq_method === "classic" ? "EOQ klasik (biaya tahunan)" : "EOQ dinamis"}
      />
    </div>
  );
}
