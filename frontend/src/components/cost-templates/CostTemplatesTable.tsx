"use client";

import type { ColumnDef } from "@tanstack/react-table";
import { useMemo } from "react";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { DataTable } from "@/components/common/DataTable";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatMoney } from "@/lib/format";
import type { CostTemplate } from "@/types/costTemplate";

export function CostTemplatesTable({
  templates,
  onSelect,
  onEdit,
  onActivate,
  onDelete,
}: {
  templates: CostTemplate[];
  onSelect?: (t: CostTemplate) => void;
  onEdit?: (t: CostTemplate) => void;
  onActivate?: (t: CostTemplate) => void;
  onDelete?: (t: CostTemplate) => void;
}) {
  const columns = useMemo<ColumnDef<CostTemplate>[]>(
    () => [
      {
        accessorKey: "name",
        header: "Template",
        cell: ({ row }) => (
          <div className="flex items-center gap-2">
            <span className="font-medium">{row.original.name}</span>
            {row.original.is_active && <Badge>Aktif</Badge>}
          </div>
        ),
      },
      {
        accessorKey: "ordering_cost",
        header: "Biaya pesan (S)",
        cell: ({ row }) => <span className="tabular-nums">{formatMoney(row.original.ordering_cost)}</span>,
      },
      {
        accessorKey: "holding_cost",
        header: "Biaya simpan (H)",
        cell: ({ row }) => <span className="tabular-nums">{formatMoney(row.original.holding_cost)}</span>,
      },
      {
        id: "items",
        header: "Item",
        enableSorting: false,
        cell: ({ row }) => `${row.original.items.length} item`,
      },
      {
        id: "actions",
        enableHiding: false,
        enableSorting: false,
        header: () => <span className="sr-only">Aksi</span>,
        cell: ({ row }) => (
          <div className="flex justify-end gap-1">
            {onSelect && (
              <Button variant="ghost" size="sm" onClick={() => onSelect(row.original)}>
                Lihat ringkasan
              </Button>
            )}
            {onActivate && !row.original.is_active && (
              <ConfirmDialog
                trigger={
                  <Button variant="ghost" size="sm">
                    Aktifkan
                  </Button>
                }
                title={`Aktifkan ${row.original.name}?`}
                description="Biaya pesan (S) dan biaya simpan (H) template ini akan dipakai untuk perhitungan reorder/EOQ & total biaya berikutnya, menggantikan template yang aktif sekarang."
                confirmLabel="Ya, aktifkan"
                onConfirm={() => onActivate(row.original)}
              />
            )}
            {onEdit && (
              <Button variant="ghost" size="sm" onClick={() => onEdit(row.original)}>
                Ubah
              </Button>
            )}
            {onDelete && (
              <ConfirmDialog
                trigger={
                  <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive">
                    Hapus
                  </Button>
                }
                title={`Hapus template ${row.original.name}?`}
                description={
                  row.original.is_active
                    ? "Template ini sedang aktif. Setelah dihapus, perhitungan EOQ kembali memakai biaya default sistem sampai template lain diaktifkan."
                    : "Template beserta seluruh item biayanya dihapus. Tindakan ini tidak bisa dibatalkan."
                }
                confirmLabel="Ya, hapus"
                onConfirm={() => onDelete(row.original)}
              />
            )}
          </div>
        ),
      },
    ],
    [onSelect, onEdit, onActivate, onDelete],
  );

  return (
    <DataTable
      columns={columns}
      data={templates}
      searchColumn="name"
      searchPlaceholder="Cari template…"
      emptyMessage="Belum ada template biaya. Tanpa template aktif, EOQ memakai biaya default sistem."
    />
  );
}
