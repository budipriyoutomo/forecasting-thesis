"use client";

import type { ColumnDef } from "@tanstack/react-table";
import { useMemo, useState } from "react";

import { DataTable } from "@/components/common/DataTable";
import { ITEM_STATUS_NOTE, ROP_FORMULA_LABEL, ReorderDetail } from "@/components/dashboard/ReorderDetail";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { formatMoney, formatNumber, formatPercent, formatQty } from "@/lib/format";
import type { Material } from "@/types/material";
import type { ReorderRecommendation, ReorderStatus } from "@/types/reorder";

export const STATUS_LABEL: Record<ReorderStatus, string> = {
  urgent: "Segera reorder",
  safe: "Aman",
  overstock: "Kelebihan stok",
};

export const STATUS_VARIANT: Record<ReorderStatus, "destructive" | "secondary" | "outline"> = {
  urgent: "destructive",
  safe: "secondary",
  overstock: "outline",
};

const FILTERS: (ReorderStatus | "all")[] = ["all", "urgent", "safe", "overstock"];

const ADJUST_LABEL: Record<string, string> = { suggested: "usulan", custom: "kustom" };

interface ReorderRow extends ReorderRecommendation {
  materialLabel: string;
  unit?: string;
}

export function isAdjusted(r: ReorderRecommendation): boolean {
  return Boolean(r.adjustment_source);
}

// Tabel rekomendasi reorder dengan filter status (Fase 5).
// `materials` opsional: bila diberikan, kolom Material menampilkan kode + nama
// alih-alih UUID mentah. `onOverride` opsional: menambah tombol Override (planner).
// CR v3.6 §6 — kolom inti saja (Material, Stok, Safety stock + hasil adjust kapasitas,
// Service level efektif, ROP + rumus, Qty pesan, Status, Biaya); Buffer & EOQ bisa
// ditampilkan lewat "Kolom", dan seluruh field ada di Sheet "Rincian" per baris.
export function ReorderTable({
  recommendations,
  materials = [],
  onOverride,
  targetServiceLevel,
  initialStatus = "all",
}: {
  recommendations: ReorderRecommendation[];
  materials?: Material[];
  onOverride?: (rec: ReorderRecommendation, materialLabel: string) => void;
  /** Target α (%) dari Pengaturan Forecast — SL efektif di bawahnya ditandai merah. */
  targetServiceLevel?: number;
  initialStatus?: ReorderStatus | "all";
}) {
  const [filter, setFilter] = useState<ReorderStatus | "all">(initialStatus);
  const [onlyAdjusted, setOnlyAdjusted] = useState(false);
  const [detail, setDetail] = useState<ReorderRow | null>(null);
  const nAdjusted = recommendations.filter(isAdjusted).length;

  const rows = useMemo<ReorderRow[]>(() => {
    const byId = new Map(materials.map((m) => [m.id, m]));
    return recommendations
      .filter((r) => filter === "all" || r.status === filter)
      .filter((r) => !onlyAdjusted || isAdjusted(r))
      .map((r) => {
        const m = byId.get(r.material_id);
        return { ...r, materialLabel: m ? `${m.code} — ${m.name}` : r.material_id, unit: m?.unit };
      });
  }, [recommendations, materials, filter, onlyAdjusted]);

  const columns = useMemo<ColumnDef<ReorderRow>[]>(
    () => [
      {
        accessorKey: "materialLabel",
        header: "Material",
        cell: ({ row }) => <span className="font-medium">{row.original.materialLabel}</span>,
      },
      {
        accessorKey: "current_stock_used",
        header: "Stok dipakai",
        cell: ({ row }) => (
          <span className="flex flex-col tabular-nums">
            {formatQty(row.original.current_stock_used ?? null, row.original.unit)}
            {row.original.stock_source && (
              <span className="text-xs text-muted-foreground">
                {row.original.stock_source === "snapshot" ? "Stok ERP" : "Input manual"}
              </span>
            )}
          </span>
        ),
      },
      {
        accessorKey: "safety_stock",
        header: "Safety stock",
        cell: ({ row }) => {
          const r = row.original;
          return (
            <span className="flex flex-col items-start gap-0.5 tabular-nums">
              {formatQty(r.safety_stock, r.unit)}
              {isAdjusted(r) && (
                <>
                  <span className="text-xs text-muted-foreground">
                    dari <s>{formatNumber(r.safety_stock_system ?? null)}</s>
                  </span>
                  <Badge variant="warning" className="font-normal">
                    Disesuaikan kapasitas ({ADJUST_LABEL[r.adjustment_source as string]})
                  </Badge>
                </>
              )}
            </span>
          );
        },
      },
      {
        accessorKey: "service_level_effective",
        header: "Service level efektif",
        cell: ({ row }) => {
          const v = row.original.service_level_effective;
          if (v == null) return <span className="text-muted-foreground">—</span>;
          const below = targetServiceLevel != null && Number(v) < targetServiceLevel;
          return (
            <span className="flex flex-col tabular-nums">
              <span className={below ? "font-semibold text-destructive" : undefined}>{formatPercent(v, 1)}</span>
              {targetServiceLevel != null && (
                <span className={below ? "text-xs text-destructive" : "text-xs text-muted-foreground"}>
                  {below ? "di bawah" : "target"} {formatPercent(targetServiceLevel, 1)}
                </span>
              )}
            </span>
          );
        },
      },
      {
        accessorKey: "buffer_stock",
        header: "Buffer",
        cell: ({ row }) => {
          const factor = row.original.waste_factor;
          return (
            <span className="flex flex-col tabular-nums">
              {formatNumber(row.original.buffer_stock ?? 0)}
              {factor != null && (
                <span className="text-xs text-muted-foreground">
                  waste {((Number(factor) - 1) * 100).toFixed(1)}%
                </span>
              )}
            </span>
          );
        },
      },
      {
        accessorKey: "reorder_point",
        header: "Reorder point",
        cell: ({ row }) => {
          const formula = ROP_FORMULA_LABEL[row.original.rop_formula_used ?? ""];
          return (
            <span className="flex flex-col tabular-nums">
              {formatNumber(row.original.reorder_point)}
              {formula && <span className="text-xs text-muted-foreground">{formula}</span>}
            </span>
          );
        },
      },
      {
        // Fase 11.9 — SATU qty pesan sesuai kebijakan (sama dengan Proyeksi Stok).
        accessorKey: "recommended_order_qty",
        header: "Qty pesan",
        cell: ({ row }) => {
          const { order_qty_policy_used: policy, order_up_to_level: s, override_qty: ov } = row.original;
          if (ov != null) {
            // Fase 11.14 — qty override planner yang berlaku; angka sistem tetap sebagai pembanding.
            return (
              <span className="flex flex-col tabular-nums">
                <span className="font-semibold">{formatNumber(ov)}</span>
                <span className="text-xs text-warning" title={row.original.override_reason ?? undefined}>
                  Override · sistem {formatNumber(row.original.recommended_order_qty)}
                </span>
              </span>
            );
          }
          return (
            <span className="flex flex-col tabular-nums">
              {formatNumber(row.original.recommended_order_qty)}
              {policy === "eoq" && <span className="text-xs text-muted-foreground">Kelipatan EOQ</span>}
              {policy === "order_up_to" && (
                <span className="text-xs text-muted-foreground">Order-up-to S = {formatNumber(s ?? null)}</span>
              )}
            </span>
          );
        },
      },
      {
        accessorKey: "eoq_qty",
        header: "EOQ (info)",
        cell: ({ row }) => (
          <span className="flex flex-col tabular-nums">
            {formatNumber(row.original.eoq_qty ?? null)}
            {row.original.eoq_method && (
              <span className="text-xs text-muted-foreground">
                {row.original.eoq_method === "classic" ? "Klasik √(2AS/iC)" : "Dinamis"}
              </span>
            )}
          </span>
        ),
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ row }) => {
          const note = ITEM_STATUS_NOTE[row.original.item_status ?? ""];
          return (
            <span className="flex flex-col items-start gap-1">
              <Badge variant={STATUS_VARIANT[row.original.status]}>{STATUS_LABEL[row.original.status]}</Badge>
              {note && <span className="text-xs text-warning">{note}</span>}
            </span>
          );
        },
      },
      {
        // CR v3.5 §5.4 — TIC per material + komponen & parameter yang dipakai.
        accessorKey: "total_inventory_cost",
        header: "Biaya persediaan",
        cell: ({ row }) => {
          const r = row.original;
          if (r.total_inventory_cost == null) return <span className="text-muted-foreground">—</span>;
          return (
            <span className="flex flex-col tabular-nums">
              {formatMoney(r.total_inventory_cost)}
              <span className="text-xs text-muted-foreground">
                Pesan {formatMoney(r.ordering_cost ?? null)} · Simpan {formatMoney(r.holding_cost ?? null)}
              </span>
              {(r.unit_price_used != null || r.holding_rate_used != null) && (
                <span className="text-xs text-muted-foreground">
                  {r.unit_price_used != null && <>C {formatMoney(r.unit_price_used, 2)}</>}
                  {r.unit_price_used != null && r.holding_rate_used != null && " · "}
                  {r.holding_rate_used != null && <>i {formatNumber(r.holding_rate_used)}%</>}
                </span>
              )}
            </span>
          );
        },
      },
      {
        id: "actions",
        header: "Aksi",
        enableHiding: false,
        enableSorting: false,
        cell: ({ row }) => (
          <span className="flex gap-2">
            <Button
              size="sm"
              variant="ghost"
              aria-label={`Rincian ${row.original.materialLabel}`}
              onClick={() => setDetail(row.original)}
            >
              Rincian
            </Button>
            {onOverride && (
              <Button
                size="sm"
                variant="outline"
                aria-label={`Override ${row.original.materialLabel}`}
                disabled={!row.original.id}
                title={row.original.id ? undefined : "Generate ulang rekomendasi untuk mengaktifkan override"}
                onClick={() => onOverride(row.original, row.original.materialLabel)}
              >
                Override
              </Button>
            )}
          </span>
        ),
      },
    ],
    [onOverride, targetServiceLevel],
  );

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <Button key={f} size="sm" variant={filter === f ? "default" : "outline"} onClick={() => setFilter(f)}>
            {f === "all" ? "Semua" : STATUS_LABEL[f]}
          </Button>
        ))}
        {nAdjusted > 0 && (
          <Button
            size="sm"
            variant={onlyAdjusted ? "default" : "outline"}
            aria-pressed={onlyAdjusted}
            onClick={() => setOnlyAdjusted((v) => !v)}
          >
            Hanya yang disesuaikan ({nAdjusted})
          </Button>
        )}
      </div>

      <DataTable
        columns={columns}
        data={rows}
        pageSize={25}
        enableColumnVisibility
        // Buffer & EOQ ada di Rincian; bisa ditampilkan lewat menu "Kolom".
        initialColumnVisibility={{ buffer_stock: false, eoq_qty: false }}
        emptyMessage="Tidak ada rekomendasi."
      />

      <Sheet open={detail !== null} onOpenChange={(open) => !open && setDetail(null)}>
        <SheetContent className="w-full overflow-y-auto sm:max-w-xl">
          {detail && (
            <>
              <SheetHeader className="mb-4">
                <SheetTitle>{detail.materialLabel}</SheetTitle>
                <SheetDescription>Rincian rekomendasi reorder & parameter yang dipakai.</SheetDescription>
              </SheetHeader>
              <ReorderDetail rec={detail} unit={detail.unit} />
            </>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
