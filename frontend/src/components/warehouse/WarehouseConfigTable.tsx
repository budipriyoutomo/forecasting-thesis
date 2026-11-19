"use client";

import type { ColumnDef } from "@tanstack/react-table";
import { useMemo } from "react";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { DataTable } from "@/components/common/DataTable";
import { Button } from "@/components/ui/button";
import { formatNumber } from "@/lib/format";
import { CAPACITY_MODE_LABELS, materialGroupKey, materialGroups, usesDus, usesPallet } from "@/lib/warehouse";
import type { Material } from "@/types/material";
import type { Product } from "@/types/product";
import type { WarehouseConfig, WarehouseTarget } from "@/types/warehouse";

interface WarehouseConfigRow extends WarehouseConfig {
  productLabel: string;
  /** Kode anggota grup material (kosong untuk produk). */
  members: string;
  /** Unit anggota grup tak lagi sama dengan `uom` kapasitas → utilisasi proyeksi tidak dihitung. */
  unitMismatch: boolean;
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
  const isMaterial = targetType === "material_group";
  const rows = useMemo<WarehouseConfigRow[]>(() => {
    if (isMaterial) {
      const groups = new Map(materialGroups(materials).map((g) => [g.key, g]));
      return configs.map((c) => {
        const g = groups.get(materialGroupKey(c.material_group));
        return {
          ...c,
          productLabel: c.material_group ?? "",
          members: g ? g.codes.join(", ") : "Belum ada material di grup ini",
          unitMismatch: Boolean(g) && g?.unit?.trim().toUpperCase() !== c.uom.trim().toUpperCase(),
        };
      });
    }
    const byId = new Map(products.map((p) => [p.id, p]));
    return configs.map((c) => {
      const id = c.product_id ?? "";
      const p = byId.get(id);
      return { ...c, productLabel: p ? `${p.code} — ${p.name}` : id, members: "", unitMismatch: false };
    });
  }, [configs, products, materials, isMaterial]);
  const dusWord = isMaterial ? "CTN" : "dus";

  const columns = useMemo<ColumnDef<WarehouseConfigRow>[]>(
    () => [
      {
        accessorKey: "productLabel",
        header: isMaterial ? "Grup material" : "Produk",
        cell: ({ row }) => <span className="font-medium">{row.original.productLabel}</span>,
      },
      ...(isMaterial
        ? [
            {
              accessorKey: "members",
              header: "Anggota",
              enableSorting: false,
              cell: ({ row }) => (
                <div className="flex flex-col">
                  <span className="text-muted-foreground">{row.original.members}</span>
                  {row.original.unitMismatch && (
                    <span className="text-xs text-destructive">
                      Unit material tidak sama dengan satuan kapasitas ({row.original.uom}) — utilisasi
                      proyeksi tidak dihitung sampai disamakan.
                    </span>
                  )}
                </div>
              ),
            } satisfies ColumnDef<WarehouseConfigRow>,
          ]
        : []),
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
                description={`Kapasitas gudang untuk ${row.original.productLabel} dihapus, sehingga ${isMaterial ? "grup material" : "produk"} itu tidak lagi ikut divalidasi kapasitas. Tindakan ini tidak bisa dibatalkan.`}
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
      searchPlaceholder={isMaterial ? "Cari grup…" : "Cari produk…"}
      emptyMessage="Belum ada konfigurasi kapasitas gudang."
    />
  );
}
