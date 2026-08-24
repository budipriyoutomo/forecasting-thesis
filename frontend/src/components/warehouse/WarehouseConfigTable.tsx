"use client";

import type { ColumnDef } from "@tanstack/react-table";
import { useMemo } from "react";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { DataTable } from "@/components/common/DataTable";
import { Button } from "@/components/ui/button";
import { formatNumber } from "@/lib/format";
import type { Product } from "@/types/product";
import type { WarehouseConfig } from "@/types/warehouse";

interface WarehouseConfigRow extends WarehouseConfig {
  productLabel: string;
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
        accessorKey: "capacity_qty",
        header: "Kapasitas",
        cell: ({ row }) => (
          <span className="tabular-nums">{formatNumber(row.original.capacity_qty)}</span>
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
