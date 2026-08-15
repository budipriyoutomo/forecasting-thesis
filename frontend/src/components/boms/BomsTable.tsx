"use client";

import type { ColumnDef } from "@tanstack/react-table";
import { useMemo } from "react";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { DataTable } from "@/components/common/DataTable";
import { Button } from "@/components/ui/button";
import { formatNumber } from "@/lib/format";
import type { Bom } from "@/types/bom";
import type { Material } from "@/types/material";
import type { Product } from "@/types/product";

/** Baris BOM yang sudah dilengkapi label, supaya sorting & pencarian bekerja atas teks
 *  yang benar-benar dilihat user — bukan atas UUID. */
interface BomRow extends Bom {
  productLabel: string;
  materialLabel: string;
}

export function BomsTable({
  boms,
  products,
  materials,
  onEdit,
  onDelete,
}: {
  boms: Bom[];
  products: Product[];
  materials: Material[];
  onEdit?: (b: Bom) => void;
  onDelete?: (b: Bom) => void;
}) {
  const rows = useMemo<BomRow[]>(() => {
    const productById = new Map(products.map((p) => [p.id, p]));
    const materialById = new Map(materials.map((m) => [m.id, m]));

    return boms.map((b) => {
      const p = productById.get(b.product_id);
      const m = materialById.get(b.material_id);
      return {
        ...b,
        productLabel: p ? `${p.code} — ${p.name}` : b.product_id,
        materialLabel: m ? `${m.code} — ${m.name}` : b.material_id,
      };
    });
  }, [boms, products, materials]);

  const columns = useMemo<ColumnDef<BomRow>[]>(
    () => [
      {
        accessorKey: "productLabel",
        header: "Produk",
        cell: ({ row }) => <span className="font-medium">{row.original.productLabel}</span>,
      },
      { accessorKey: "materialLabel", header: "Material" },
      {
        accessorKey: "qty_per_unit",
        header: "Qty / unit",
        cell: ({ row }) => (
          <span className="tabular-nums">{formatNumber(row.original.qty_per_unit, 4)}</span>
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
                title="Hapus baris BOM ini?"
                description={`Takaran ${row.original.materialLabel} untuk ${row.original.productLabel} dihapus, sehingga material itu tidak lagi ikut diturunkan saat forecast produk tersebut. Tindakan ini tidak bisa dibatalkan.`}
                confirmLabel="Ya, hapus baris"
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
      searchColumn="materialLabel"
      searchPlaceholder="Cari material…"
      emptyMessage="Belum ada baris BOM."
    />
  );
}
