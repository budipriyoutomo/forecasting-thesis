"use client";

import { useMemo } from "react";

import { StatTile } from "@/components/dashboard/StatTile";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatMoney, formatNumber } from "@/lib/format";
import type { CostTemplate, CostTemplateSummary } from "@/types/costTemplate";
import type { Material } from "@/types/material";

// Ringkasan satu template (Fase 10): komponen biaya per bulan, saran H (referensi —
// EOQ tetap memakai H manual), dan biaya pembelian dari harga master material.
export function CostTemplateSummaryPanel({
  template,
  summary,
  materials,
}: {
  template: CostTemplate;
  summary: CostTemplateSummary;
  materials: Material[];
}) {
  const priced = useMemo(
    () =>
      [...materials]
        .filter((m) => m.unit_price != null)
        .sort((a, b) => a.code.localeCompare(b.code)),
    [materials],
  );
  const unpriced = materials.length - priced.length;

  return (
    <section className="flex flex-col gap-4">
      <h3 className="text-sm font-medium text-muted-foreground">Ringkasan — {template.name}</h3>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label="Depresiasi aset / bulan" value={formatMoney(summary.total_depreciation_monthly)} />
        <StatTile label="Overhead / bulan" value={formatMoney(summary.total_overhead_monthly)} />
        <StatTile
          label="Total biaya gudang / bulan"
          value={formatMoney(summary.total_monthly)}
          hint={`Kapasitas gudang ${formatNumber(summary.total_capacity_dus)} dus`}
        />
        {summary.suggested_holding_cost !== null ? (
          <StatTile
            label="Saran H / dus / bulan"
            value={formatMoney(summary.suggested_holding_cost, 2)}
            hint={`${formatMoney(summary.holding_cost, 2)} dipakai EOQ`}
          />
        ) : (
          <StatTile
            label="Saran H / dus / bulan"
            value="—"
            hint="Isi kapasitas gudang dulu agar saran H bisa dihitung."
          />
        )}
      </div>

      <div className="flex flex-col gap-2">
        <h4 className="text-sm font-medium">Biaya pembelian material</h4>
        <p className="text-xs text-muted-foreground">
          Dari harga beli di master material — ditampilkan sebagai informasi, tidak dijumlahkan
          ke total biaya persediaan (TIC).
          {unpriced > 0 && (
            <span className="text-amber-600 dark:text-amber-500">
              {" "}
              {unpriced} material belum punya harga.
            </span>
          )}
        </p>
        {priced.length > 0 && (
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Material</TableHead>
                  <TableHead className="text-right">Harga beli</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {priced.map((m) => (
                  <TableRow key={m.id}>
                    <TableCell>
                      {m.code} — {m.name}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatMoney(m.unit_price, 2)} / {m.unit}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>
    </section>
  );
}
