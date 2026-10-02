"use client";

import type { ColumnDef } from "@tanstack/react-table";
import { useMemo } from "react";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { DataTable } from "@/components/common/DataTable";
import { Button } from "@/components/ui/button";
import { formatNumber } from "@/lib/format";
import { CAPACITY_MODE_LABELS, usesDus, usesPallet } from "@/lib/warehouse";
import type { Product } from "@/types/product";
import type { WarehouseConfig } from "@/types/warehouse";

interface WarehouseConfigRow extends WarehouseConfig {
  productLabel: string;
}

// "10 pallet × 60 + 25 dus" / "10 pallet × 60" / "25 dus"
function capacityBreakdown(c: WarehouseConfig): string {
  const parts: string[] = [];
  if (usesPallet(c.capacity_mode))
    parts.push(`${formatNumber(c.pallet_qty)} pallet × ${formatNumber(c.dus_per_pallet)}`);
  if (usesDus(c.capacity_mode)) parts.push(`${formatNumber(c.dus_qty)} dus`);
  return parts.join(" + ");
}

export function WarehouseConfigTable({
  configs,
  products,
  onEdit,
  onDelete,
}: {
  configs: WarehouseConfig[];
  products: Product[];
  onEdit?: (c: WarehouseConfig) => void;
  onDelete?: (c: WarehouseConfig) => void;
}) {
  const rows = useMemo<WarehouseConfigRow[]>(() => {
    const productById = new Map(products.map((p) => [p.id, p]));
    return configs.map((c) => {
      const p = productById.get(c.product_id);
      return { ...c, productLabel: p ? `${p.code} — ${p.name}` : c.product_id };
    });
  }, [configs, products]);

  const columns = useMemo<ColumnDef<WarehouseConfigRow>[]>(
    () => [
      {
        accessorKey: "productLabel",
        header: "Produk",
        cell: ({ row }) => <span className="font-medium">{row.original.productLabel}</span>,
      },
      {
        accessorKey: "capacity_mode",
        header: "Mode",
        cell: ({ row }) => CAPACITY_MODE_LABELS[row.original.capacity_mode],
      },
      {
        id: "breakdown",
        header: "Rincian",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="tabular-nums text-muted-foreground">
            {capacityBreakdown(row.original)}
          </span>
        ),
      },
      {
        accessorKey: "capacity_dus",
        header: "Dalam dus",
        cell: ({ row }) => (
          <span className="tabular-nums">{formatNumber(row.original.capacity_dus)} dus</span>
        ),
      },
      {
        accessorKey: "capacity_qty",
        header: "Kapasitas",
        cell: ({ row }) => (
          <span className="tabular-nums font-medium">
            {formatNumber(row.original.capacity_qty)} {row.original.uom}
          </span>
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
                title="Hapus konfigurasi kapasitas ini?"
                description={`Kapasitas gudang untuk ${row.original.productLabel} dihapus, sehingga produk itu tidak lagi ikut divalidasi kapasitas. Tindakan ini tidak bisa dibatalkan.`}
                confirmLabel="Ya, hapus"
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
      data={rows}
      searchColumn="productLabel"
      searchPlaceholder="Cari produk…"
      emptyMessage="Belum ada konfigurasi kapasitas gudang."
    />
  );
}
