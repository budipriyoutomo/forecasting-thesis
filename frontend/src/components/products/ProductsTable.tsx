"use client";

import type { ColumnDef } from "@tanstack/react-table";
import { useMemo } from "react";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { DataTable } from "@/components/common/DataTable";
import { Button } from "@/components/ui/button";
import type { Product } from "@/types/product";

export function ProductsTable({
  products,
  onEdit,
  onDelete,
}: {
  products: Product[];
  onEdit?: (p: Product) => void;
  onDelete?: (p: Product) => void;
}) {
  const columns = useMemo<ColumnDef<Product>[]>(
    () => [
      {
        accessorKey: "code",
        header: "Kode SKU",
        cell: ({ row }) => <span className="font-medium">{row.original.code}</span>,
      },
      { accessorKey: "name", header: "Nama" },
      {
        accessorKey: "category",
        header: "Kategori",
        cell: ({ row }) => row.original.category ?? "—",
      },
      { accessorKey: "unit", header: "Satuan" },
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
                title={`Hapus produk ${row.original.code}?`}
                description="Produk hilang dari master data dan tidak bisa dipilih untuk forecast berikutnya. Baris BOM yang menunjuk produk ini ikut terdampak. Tindakan ini tidak bisa dibatalkan."
                confirmLabel="Ya, hapus produk"
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
      data={products}
      searchColumn="name"
      searchPlaceholder="Cari nama produk…"
      enableColumnVisibility
      emptyMessage="Belum ada produk."
    />
  );
}
