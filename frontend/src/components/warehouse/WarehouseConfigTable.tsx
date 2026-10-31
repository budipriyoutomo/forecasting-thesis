"use client";

import type { ColumnDef } from "@tanstack/react-table";
import { useMemo } from "react";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { DataTable } from "@/components/common/DataTable";
import { Button } from "@/components/ui/button";
import { formatNumber } from "@/lib/format";
import { CAPACITY_MODE_LABELS, usesDus, usesPallet } from "@/lib/warehouse";
import type { Material } from "@/types/material";
import type { Product } from "@/types/product";
import type { WarehouseConfig, WarehouseTarget } from "@/types/warehouse";

interface WarehouseConfigRow extends WarehouseConfig {
  productLabel: string;
}

// "10 pallet × 60 + 25 dus" / "10 pallet × 60" / "25 dus" — material memakai CTN (Fase 11.6)
function capacityBreakdown(c: WarehouseConfig, dusWord: string): string {
  const parts: string[] = [];
  if (usesPallet(c.capacity_mode))
    parts.push(`${formatNumber(c.pallet_qty)} pallet × ${formatNumber(c.dus_per_pallet)}`);
  if (usesDus(c.capacity_mode)) parts.push(`${formatNumber(c.dus_qty)} ${dusWord}`);
  return parts.join(" + ");
}

export function WarehouseConfigTable({
  configs,
  products,
  materials = [],
  targetType = "product",
  onEdit,
  onDelete,
}: {
  configs: WarehouseConfig[];
  products: Product[];
  materials?: Material[];
  targetType?: WarehouseTarget;
  onEdit?: (c: WarehouseConfig) => void;
  onDelete?: (c: WarehouseConfig) => void;
}) {
  const rows = useMemo<WarehouseConfigRow[]>(() => {
    const byId = new Map<string, { code: string; name: string }>(
      (targetType === "material" ? materials : products).map((p) => [p.id, p]),
    );
    return configs.map((c) => {
      const id = (targetType === "material" ? c.material_id : c.product_id) ?? "";
      const p = byId.get(id);
      return { ...c, productLabel: p ? `${p.code} — ${p.name}` : id };
    });
  }, [configs, products, materials, targetType]);
  const isMaterial = targetType === "material";
  const dusWord = isMaterial ? "CTN" : "dus";

  const columns = useMemo<ColumnDef<WarehouseConfigRow>[]>(
    () => [
      {
        accessorKey: "productLabel",
        header: isMaterial ? "Material" : "Produk",
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
            {capacityBreakdown(row.original, dusWord)}
          </span>
        ),
      },
      {
        accessorKey: "capacity_dus",
        header: `Dalam ${dusWord}`,
        cell: ({ row }) => (
          <span className="tabular-nums">{formatNumber(row.original.capacity_dus)} {dusWord}</span>
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
    [onEdit, onDelete, isMaterial, dusWord],
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
