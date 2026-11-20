"use client";

import type { ColumnDef } from "@tanstack/react-table";
import { useMemo } from "react";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { DataTable } from "@/components/common/DataTable";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { ExternalVariable, ExternalVariableCoverage } from "@/types/externalVariable";

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

// CR v3.4 §4.2 — periode terisi / periode demand + horizon. < 100% → variabel akan di-drop engine.
function CoverageCell({ coverage }: { coverage?: ExternalVariableCoverage }) {
  if (!coverage || coverage.n_expected === 0) return <span className="text-muted-foreground">—</span>;
  const pct = Math.round((coverage.n_filled / coverage.n_expected) * 100);
  const missing = coverage.missing_periods;
  const title = missing.length
    ? `Belum terisi: ${missing.slice(0, 6).join(", ")}${missing.length > 6 ? ` +${missing.length - 6} lagi` : ""}`
    : "Lengkap untuk histori + horizon";
  return (
    <span title={title} className={cn("whitespace-nowrap tabular-nums", pct < 100 && "font-medium text-destructive")}>
      {`${coverage.n_filled}/${coverage.n_expected} (${pct}%)`}
    </span>
  );
}

export function ExternalVariablesTable({
  variables,
  coverage,
  onToggle,
  onEdit,
  onClearValues,
  onDelete,
  onViewValues,
}: {
  variables: ExternalVariable[];
  /** Kelengkapan per variable_id (opsional). */
  coverage?: Record<string, ExternalVariableCoverage>;
  /** Tanpa handler (role tanpa izin `extvar.define`) status aktif tampil read-only. */
  onToggle?: (v: ExternalVariable, next: boolean) => void;
  onEdit?: (v: ExternalVariable) => void;
  onClearValues?: (v: ExternalVariable) => void;
  onDelete?: (v: ExternalVariable) => void;
  /** CR v3.5 §5.2 — buka nilai per periode (baca, semua role). */
  onViewValues?: (v: ExternalVariable) => void;
}) {
  const columns = useMemo<ColumnDef<ExternalVariable>[]>(
    () => [
      {
        accessorKey: "is_active",
        header: "Aktif",
        cell: ({ row }) =>
          onToggle ? (
            <ActiveSwitch variable={row.original} onToggle={onToggle} />
          ) : (
            <Badge variant={row.original.is_active ? "secondary" : "outline"}>
              {row.original.is_active ? "Aktif" : "Nonaktif"}
            </Badge>
          ),
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
        id: "coverage",
        header: "Kelengkapan",
        enableSorting: false,
        cell: ({ row }) => <CoverageCell coverage={coverage?.[row.original.id]} />,
      },
      {
        id: "actions",
        enableHiding: false,
        enableSorting: false,
        header: () => <span className="sr-only">Aksi</span>,
        cell: ({ row }) => (
          <div className="flex justify-end gap-1">
            {onViewValues && row.original.n_values > 0 && (
              <Button variant="ghost" size="sm" onClick={() => onViewValues(row.original)}>
                Lihat nilai
              </Button>
            )}
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
    [coverage, onToggle, onEdit, onClearValues, onDelete, onViewValues],
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
