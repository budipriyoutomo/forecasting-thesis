"use client";

import { useMemo } from "react";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { summarizeBomCosts } from "@/lib/bom";
import { formatMoney } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Bom } from "@/types/bom";
import type { Product } from "@/types/product";

// Biaya material per unit produk (Σ qty × harga material) dibanding HPP (Fase 10).
// Hanya pembanding — HPP tetap isian master produk, tidak ditimpa angka ini.
export function BomCostSummary({ boms, products }: { boms: Bom[]; products: Product[] }) {
  const rows = useMemo(() => summarizeBomCosts(boms, products), [boms, products]);
  const productById = useMemo(() => new Map(products.map((p) => [p.id, p])), [products]);

  if (rows.length === 0) return null;

  return (
    <section className="flex flex-col gap-2">
      <h3 className="text-sm font-medium text-muted-foreground">
        Biaya material per unit produk
      </h3>
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Produk</TableHead>
              <TableHead className="text-right">Biaya material</TableHead>
              <TableHead className="text-right">HPP</TableHead>
              <TableHead className="text-right">HPP − biaya material</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((r) => {
              const p = productById.get(r.product_id);
              return (
                <TableRow key={r.product_id}>
                  <TableCell>
                    <span className="font-medium">{p ? `${p.code} — ${p.name}` : r.product_id}</span>
                    {r.n_without_price > 0 && (
                      <p className="text-xs text-amber-600 dark:text-amber-500">
                        {r.n_without_price} material belum punya harga — total belum lengkap
                      </p>
                    )}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {formatMoney(r.material_cost, 2)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {formatMoney(r.cost_price, 2)}
                  </TableCell>
                  <TableCell
                    className={cn(
                      "text-right tabular-nums",
                      r.margin_vs_hpp !== null && r.margin_vs_hpp < 0 && "text-destructive",
                    )}
                  >
                    {formatMoney(r.margin_vs_hpp, 2)}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </section>
  );
}
