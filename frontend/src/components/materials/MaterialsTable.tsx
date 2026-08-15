"use client";

import type { ColumnDef } from "@tanstack/react-table";
import { useMemo } from "react";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { DataTable } from "@/components/common/DataTable";
import { Button } from "@/components/ui/button";
import { formatNumber } from "@/lib/format";
import type { Material } from "@/types/material";

export function MaterialsTable({
  materials,
  onEdit,
  onDelete,
}: {
  materials: Material[];
  onEdit?: (m: Material) => void;
  onDelete?: (m: Material) => void;
}) {
  const columns = useMemo<ColumnDef<Material>[]>(
    () => [
      {
        accessorKey: "code",
        header: "Kode",
        cell: ({ row }) => <span className="font-medium">{row.original.code}</span>,
      },
      { accessorKey: "name", header: "Nama" },
      { accessorKey: "unit", header: "Satuan" },
      {
        accessorKey: "lead_time_days",
        header: "Lead time",
        cell: ({ row }) => `${row.original.lead_time_days} hari`,
      },
      {
        accessorKey: "moq",
        header: "MOQ",
        cell: ({ row }) => (
          <span className="tabular-nums">{formatNumber(row.original.moq)}</span>
        ),
      },
      {
        id: "actions",
        enableHiding: false,
        enableSorting: false,
        header: () => <span className="sr-only">Aksi</span>,
        cell: ({ row }) => (
          <div className="flex justify-end gap-1">
            {onEdit && (
              <Button variant="ghost" size="sm" onClick={() => onEdit(row.original)}>
                Ubah
              </Button>
            )}
            {onDelete && (
              <ConfirmDialog
                trigger={
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive hover:text-destructive"
                  >
                    Hapus
                  </Button>
                }
                title={`Hapus material ${row.original.code}?`}
                description="Material hilang dari master data beserta lead time dan MOQ-nya. Baris BOM yang memakai material ini ikut terdampak, begitu pula perhitungan reorder berikutnya. Tindakan ini tidak bisa dibatalkan."
                confirmLabel="Ya, hapus material"
                onConfirm={() => onDelete(row.original)}
              />
            )}
          </div>
        ),
      },
    ],
    [onEdit, onDelete],
  );

  return (
    <DataTable
      columns={columns}
      data={materials}
      searchColumn="name"
      searchPlaceholder="Cari nama material…"
      enableColumnVisibility
      emptyMessage="Belum ada material."
    />
  );
}
