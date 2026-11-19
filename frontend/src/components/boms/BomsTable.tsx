"use client";

import type { ColumnDef } from "@tanstack/react-table";
import { useMemo } from "react";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { DataTable } from "@/components/common/DataTable";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { flattenBomLevels, type BomLevelRow } from "@/lib/bom";
import { formatMoney, formatNumber } from "@/lib/format";
import type { Bom, MaterialComponent } from "@/types/bom";
import type { Material } from "@/types/material";
import type { Product } from "@/types/product";

/** Baris BOM (level 1 dari `boms`, level 2+ dari komponen material) yang sudah dilengkapi
 *  label, supaya sorting & pencarian bekerja atas teks yang dilihat user — bukan UUID. */
interface BomRow extends BomLevelRow {
  productLabel: string;
  materialLabel: string;
  parentLabel: string | null;
  line_cost: string | null;
}

export function BomsTable({
  boms,
  components = [],
  products,
  materials,
  onEdit,
  onDelete,
}: {
  boms: Bom[];
  /** Komponen level 2+ (19 Nov 2026) — ditampilkan di bawah material induknya. */
  components?: MaterialComponent[];
  products: Product[];
  materials: Material[];
  onEdit?: (b: Bom) => void;
  onDelete?: (b: Bom) => void;
}) {
  const rows = useMemo<BomRow[]>(() => {
    const productById = new Map(products.map((p) => [p.id, p]));
    const materialById = new Map(materials.map((m) => [m.id, m]));

    const label = (id: string) => {
      const m = materialById.get(id);
      return m ? `${m.code} — ${m.name}` : id;
    };

    return flattenBomLevels(boms, components).map((r) => {
      const p = productById.get(r.product_id);
      return {
        ...r,
        productLabel: p ? `${p.code} — ${p.name}` : r.product_id,
        materialLabel: label(r.material_id),
        parentLabel: r.parent_material_id ? (materialById.get(r.parent_material_id)?.code ?? r.parent_material_id) : null,
        line_cost: r.bom?.line_cost ?? null,
      };
    });
  }, [boms, components, products, materials]);

  const columns = useMemo<ColumnDef<BomRow>[]>(
    () => [
      {
        accessorKey: "productLabel",
        header: "Produk",
        cell: ({ row }) => <span className="font-medium">{row.original.productLabel}</span>,
      },
      {
        accessorKey: "level",
        header: "Level",
        enableSorting: false,
        cell: ({ row }) => (
          <Badge variant={row.original.level === 1 ? "secondary" : "outline"} className="tabular-nums">
            {row.original.level}
          </Badge>
        ),
      },
      {
        accessorKey: "materialLabel",
        header: "Material",
        cell: ({ row }) => (
          <div className="flex flex-col" style={{ paddingLeft: `${(row.original.level - 1) * 1.25}rem` }}>
            <span>{row.original.materialLabel}</span>
            {row.original.parentLabel && (
              <span className="text-xs text-muted-foreground">komponen dari {row.original.parentLabel}</span>
            )}
          </div>
        ),
      },
      {
        accessorKey: "qty_per_unit",
        header: "Qty / unit",
        cell: ({ row }) => (
          <span className="tabular-nums">{formatNumber(row.original.qty_per_unit, 4)}</span>
        ),
      },
      {
        accessorKey: "line_cost",
        header: "Biaya / unit produk",
        cell: ({ row }) =>
          row.original.level === 1 ? (
            <span className="tabular-nums">{formatMoney(row.original.line_cost ?? null, 2)}</span>
          ) : (
            <span className="text-xs text-muted-foreground">Informasi</span>
          ),
      },
      {
        id: "actions",
        enableHiding: false,
        enableSorting: false,
        header: () => <span className="sr-only">Aksi</span>,
        cell: ({ row }) => {
          const bom = row.original.bom;
          if (!bom) return null; // level 2+ dikelola lewat Struktur BOM multi-level
          return (
          <div className="flex justify-end gap-1">
            {onEdit && (
              <Button variant="ghost" size="sm" onClick={() => onEdit(bom)}>
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
                onConfirm={() => onDelete(bom)}
              />
            )}
          </div>
          );
        },
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
