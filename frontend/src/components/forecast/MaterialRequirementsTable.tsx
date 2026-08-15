"use client";

import type { ColumnDef } from "@tanstack/react-table";
import { useMemo, useState } from "react";

import { DataTable } from "@/components/common/DataTable";
import { AuditTrail } from "@/components/override/AuditTrail";
import { OverrideForm } from "@/components/override/OverrideForm";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { formatNumber, formatPercent } from "@/lib/format";
import type { MaterialRequirement } from "@/types/forecast";
import type { Material } from "@/types/material";

interface RequirementRow extends MaterialRequirement {
  materialLabel: string;
}

// Kebutuhan raw material hasil breakdown BOM per run (Fase 5, dibaca Fase 9).
// Tiap baris bisa di-override planner — `target_id`-nya adalah `id` baris ini
// (AGENTS.md §5 "Planner Override — non-negotiable").
//
// `materials` opsional: bila diberikan, kolom Material menampilkan kode + nama
// alih-alih UUID mentah.
export function MaterialRequirementsTable({
  requirements,
  materials = [],
}: {
  requirements: MaterialRequirement[];
  materials?: Material[];
}) {
  const [editing, setEditing] = useState<MaterialRequirement | null>(null);

  const rows = useMemo<RequirementRow[]>(() => {
    const byId = new Map(materials.map((m) => [m.id, m]));
    return requirements.map((req) => {
      const m = byId.get(req.material_id);
      return { ...req, materialLabel: m ? `${m.code} — ${m.name}` : req.material_id };
    });
  }, [requirements, materials]);

  const columns = useMemo<ColumnDef<RequirementRow>[]>(
    () => [
      {
        accessorKey: "materialLabel",
        header: "Material",
        cell: ({ row }) => <span className="font-medium">{row.original.materialLabel}</span>,
      },
      {
        accessorKey: "forecast_qty",
        header: "Kebutuhan (forecast)",
        cell: ({ row }) => (
          <span className="tabular-nums">{formatNumber(row.original.forecast_qty)}</span>
        ),
      },
      {
        accessorKey: "standard_usage_qty",
        header: "Standar Pemakaian",
        cell: ({ row }) => (
          <span className="tabular-nums">{formatNumber(row.original.standard_usage_qty)}</span>
        ),
      },
      {
        accessorKey: "actual_usage_qty",
        header: "Aktual Pemakaian",
        cell: ({ row }) => (
          <span className="tabular-nums">{formatNumber(row.original.actual_usage_qty)}</span>
        ),
      },
      {
        accessorKey: "buffer_stock_pct",
        header: "Buffer",
        cell: ({ row }) => (
          <span className="tabular-nums">{formatPercent(row.original.buffer_stock_pct)}</span>
        ),
      },
      {
        id: "actions",
        enableHiding: false,
        enableSorting: false,
        header: () => <span className="sr-only">Aksi</span>,
        cell: ({ row }) => (
          <div className="flex justify-end">
            <Button variant="ghost" size="sm" onClick={() => setEditing(row.original)}>
              Override
            </Button>
          </div>
        ),
      },
    ],
    [],
  );

  return (
    <>
      <DataTable
        columns={columns}
        data={rows}
        emptyMessage="Belum ada kebutuhan material untuk run ini — produk yang diforecast belum punya BOM."
      />

      <Dialog open={editing !== null} onOpenChange={(open) => !open && setEditing(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            {/* Judul sengaja tidak memuat frasa "kebutuhan material": DialogContent
                memakainya sebagai aria-label, sehingga akan bentrok dengan label
                field "Kebutuhan material baru" saat dicari lewat label. */}
            <DialogTitle>Override baris material</DialogTitle>
            <DialogDescription>
              Alasan wajib diisi dan tersimpan di audit trail bersama nilai sebelumnya.
            </DialogDescription>
          </DialogHeader>
          {editing && (
            <>
              <OverrideForm
                targetType="material_requirement"
                targetId={editing.id}
                field="forecast_qty"
                label="Kebutuhan material baru"
                onDone={() => setEditing(null)}
              />
              {/* Riwayat ditaruh sepanel dengan formnya: planner perlu melihat apakah
                  baris ini sudah pernah di-override (dan alasannya) sebelum menimpanya. */}
              <div className="flex flex-col gap-2 border-t pt-4">
                <h3 className="text-sm font-medium">Riwayat override baris ini</h3>
                <AuditTrail targetId={editing.id} />
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
