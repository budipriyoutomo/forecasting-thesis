"use client";

import type { ColumnDef } from "@tanstack/react-table";
import { useMemo } from "react";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { DataTable } from "@/components/common/DataTable";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { ExternalVariable } from "@/types/externalVariable";

// Toggle aktif langsung di tabel: hanya variabel aktif yang ikut jadi fitur model ML.
function ActiveSwitch({ variable, onToggle }: { variable: ExternalVariable; onToggle: (v: ExternalVariable, next: boolean) => void }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={variable.is_active}
      aria-label={`Aktifkan ${variable.code}`}
      onClick={() => onToggle(variable, !variable.is_active)}
      className={cn(
        "relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors",
        variable.is_active ? "bg-primary" : "bg-muted-foreground/30",
      )}
    >
      <span
        className={cn(
          "inline-block size-4 rounded-full bg-background shadow transition-transform",
          variable.is_active ? "translate-x-4" : "translate-x-0.5",
        )}
      />
    </button>
  );
}

export function ExternalVariablesTable({
  variables,
  onToggle,
  onEdit,
  onClearValues,
  onDelete,
}: {
  variables: ExternalVariable[];
  onToggle: (v: ExternalVariable, next: boolean) => void;
  onEdit?: (v: ExternalVariable) => void;
  onClearValues?: (v: ExternalVariable) => void;
  onDelete?: (v: ExternalVariable) => void;
}) {
  const columns = useMemo<ColumnDef<ExternalVariable>[]>(
    () => [
      {
        accessorKey: "is_active",
        header: "Aktif",
        cell: ({ row }) => <ActiveSwitch variable={row.original} onToggle={onToggle} />,
      },
      {
        accessorKey: "code",
        header: "Kode",
        cell: ({ row }) => <span className="font-mono text-sm">{row.original.code}</span>,
      },
      { accessorKey: "name", header: "Nama" },
      {
        accessorKey: "value_type",
        header: "Tipe",
        cell: ({ row }) => (
          <Badge variant="outline">{row.original.value_type === "flag" ? "Flag (0/1)" : "Numerik"}</Badge>
        ),
      },
      {
        accessorKey: "scope",
        header: "Cakupan",
        cell: ({ row }) => (row.original.scope === "product" ? "Per produk" : "Global"),
      },
      { accessorKey: "unit", header: "Satuan", cell: ({ row }) => row.original.unit ?? "—" },
      {
        accessorKey: "n_values",
        header: "Jumlah nilai",
        cell: ({ row }) => <span className="tabular-nums">{row.original.n_values}</span>,
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
            {onClearValues && row.original.n_values > 0 && (
              <ConfirmDialog
                trigger={<Button variant="ghost" size="sm">Kosongkan nilai</Button>}
                title={`Kosongkan nilai ${row.original.code}?`}
                description="Seluruh nilai per periode variabel ini dihapus. Definisinya tetap ada dan bisa diisi ulang lewat import."
                confirmLabel="Ya, kosongkan"
                onConfirm={() => onClearValues(row.original)}
              />
            )}
            {onDelete && (
              <ConfirmDialog
                trigger={
                  <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive">
                    Hapus
                  </Button>
                }
                title={`Hapus variabel ${row.original.code}?`}
                description="Variabel beserta seluruh nilainya dihapus. Forecast run berikutnya tidak lagi memakai variabel ini. Tindakan ini tidak bisa dibatalkan."
                confirmLabel="Ya, hapus variabel"
                onConfirm={() => onDelete(row.original)}
              />
            )}
          </div>
        ),
      },
    ],
    [onToggle, onEdit, onClearValues, onDelete],
  );

  return (
    <DataTable
      columns={columns}
      data={variables}
      searchColumn="name"
      searchPlaceholder="Cari variabel…"
      emptyMessage="Belum ada variabel eksternal."
    />
  );
}
