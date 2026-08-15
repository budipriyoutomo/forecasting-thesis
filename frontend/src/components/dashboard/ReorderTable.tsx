"use client";

import type { ColumnDef } from "@tanstack/react-table";
import { useMemo, useState } from "react";

import { DataTable } from "@/components/common/DataTable";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatNumber } from "@/lib/format";
import type { Material } from "@/types/material";
import type { ReorderRecommendation, ReorderStatus } from "@/types/reorder";

const STATUS_LABEL: Record<ReorderStatus, string> = {
  urgent: "Segera reorder",
  safe: "Aman",
  overstock: "Kelebihan stok",
};

const STATUS_VARIANT: Record<ReorderStatus, "destructive" | "secondary" | "outline"> = {
  urgent: "destructive",
  safe: "secondary",
  overstock: "outline",
};

const FILTERS: (ReorderStatus | "all")[] = ["all", "urgent", "safe", "overstock"];

interface ReorderRow extends ReorderRecommendation {
  materialLabel: string;
}

// Tabel rekomendasi reorder dengan filter status (Fase 5).
// `materials` opsional: bila diberikan, kolom Material menampilkan kode + nama
// alih-alih UUID mentah.
export function ReorderTable({
  recommendations,
  materials = [],
}: {
  recommendations: ReorderRecommendation[];
  materials?: Material[];
}) {
  const [filter, setFilter] = useState<ReorderStatus | "all">("all");

  const rows = useMemo<ReorderRow[]>(() => {
    const byId = new Map(materials.map((m) => [m.id, m]));
    const filtered =
      filter === "all" ? recommendations : recommendations.filter((r) => r.status === filter);

    return filtered.map((r) => {
      const m = byId.get(r.material_id);
      return { ...r, materialLabel: m ? `${m.code} — ${m.name}` : r.material_id };
    });
  }, [recommendations, materials, filter]);

  const columns = useMemo<ColumnDef<ReorderRow>[]>(
    () => [
      {
        accessorKey: "materialLabel",
        header: "Material",
        cell: ({ row }) => <span className="font-medium">{row.original.materialLabel}</span>,
      },
      {
        accessorKey: "safety_stock",
        header: "Safety stock",
        cell: ({ row }) => (
          <span className="tabular-nums">{formatNumber(row.original.safety_stock)}</span>
        ),
      },
      {
        accessorKey: "reorder_point",
        header: "Reorder point",
        cell: ({ row }) => (
          <span className="tabular-nums">{formatNumber(row.original.reorder_point)}</span>
        ),
      },
      {
        accessorKey: "recommended_order_qty",
        header: "Order qty",
        cell: ({ row }) => (
          <span className="tabular-nums">{formatNumber(row.original.recommended_order_qty)}</span>
        ),
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ row }) => (
          <Badge variant={STATUS_VARIANT[row.original.status]}>
            {STATUS_LABEL[row.original.status]}
          </Badge>
        ),
      },
    ],
    [],
  );

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <Button
            key={f}
            size="sm"
            variant={filter === f ? "default" : "outline"}
            onClick={() => setFilter(f)}
          >
            {f === "all" ? "Semua" : STATUS_LABEL[f]}
          </Button>
        ))}
      </div>

      <DataTable columns={columns} data={rows} emptyMessage="Tidak ada rekomendasi." />
    </div>
  );
}
