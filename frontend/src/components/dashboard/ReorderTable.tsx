"use client";

import { useState } from "react";

import { cn } from "@/lib/utils";
import type { ReorderRecommendation, ReorderStatus } from "@/types/reorder";

const STATUS_STYLE: Record<ReorderStatus, string> = {
  urgent: "text-destructive font-medium",
  safe: "text-foreground",
  overstock: "text-amber-600",
};

const STATUS_LABEL: Record<ReorderStatus, string> = {
  urgent: "Segera reorder",
  safe: "Aman",
  overstock: "Kelebihan stok",
};

const FILTERS: (ReorderStatus | "all")[] = ["all", "urgent", "safe", "overstock"];

// Tabel rekomendasi reorder dengan filter status (Fase 5).
export function ReorderTable({ recommendations }: { recommendations: ReorderRecommendation[] }) {
  const [filter, setFilter] = useState<ReorderStatus | "all">("all");
  const rows = filter === "all" ? recommendations : recommendations.filter((r) => r.status === filter);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex gap-2">
        {FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={cn(
              "rounded-md border px-3 py-1 text-sm",
              filter === f ? "bg-primary text-primary-foreground" : "hover:bg-accent",
            )}
          >
            {f === "all" ? "Semua" : STATUS_LABEL[f]}
          </button>
        ))}
      </div>

      {rows.length === 0 ? (
        <p className="text-sm text-muted-foreground">Tidak ada rekomendasi.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="py-2 pr-4">Material</th>
                <th className="py-2 pr-4">Safety stock</th>
                <th className="py-2 pr-4">Reorder point</th>
                <th className="py-2 pr-4">Order qty</th>
                <th className="py-2 pr-4">Status</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.material_id} className="border-b">
                  <td className="py-2 pr-4 font-medium">{r.material_id}</td>
                  <td className="py-2 pr-4">{r.safety_stock}</td>
                  <td className="py-2 pr-4">{r.reorder_point}</td>
                  <td className="py-2 pr-4">{r.recommended_order_qty}</td>
                  <td className={cn("py-2 pr-4", STATUS_STYLE[r.status])}>{STATUS_LABEL[r.status]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
