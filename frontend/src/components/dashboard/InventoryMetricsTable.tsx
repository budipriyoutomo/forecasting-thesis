"use client";

import { EmptyState } from "@/components/common/EmptyState";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatMoney } from "@/lib/format";
import type { Material } from "@/types/material";
import type { InventoryMetric } from "@/types/metrics";
import type { Product } from "@/types/product";

const SCOPE_LABEL: Record<string, string> = {
  baseline: "Existing (baseline)",
  forecastiq: "ForecastIQ",
};

// Format khusus tabel ini, bukan formatter umum: nilainya rasio 0..1 yang harus
// tampil 1 desimal, dan turnover dalam "kali" dengan 2 desimal.
function pct(value: string): string {
  return `${(Number(value) * 100).toFixed(1)}%`;
}

function turns(value: string): string {
  return `${Number(value).toFixed(2)}×`;
}

// Evaluasi kinerja inventory per scope (Fase 7): baseline (actual vs planning)
// vs forecastiq (actual vs forecast ForecastIQ) — membuktikan perbaikan thesis.
// Tetap memakai tabel polos, bukan DataTable: isinya perbandingan dua baris,
// jadi pencarian dan penomoran halaman hanya menambah derau.
// Fase 11.7: baris level material (dari proyeksi stok) + inventory days & shortage cost.
export function InventoryMetricsTable({
  metrics,
  materials = [],
  products = [],
}: {
  metrics: InventoryMetric[];
  materials?: Material[];
  products?: Product[];
}) {
  const codeOf = new Map<string, string>([...products, ...materials].map((x) => [x.id, x.code]));
  if (metrics.length === 0) {
    return <EmptyState message="Belum ada metrik inventory untuk run ini." />;
  }

  return (
    <div className="overflow-x-auto rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Target</TableHead>
            <TableHead>Scope</TableHead>
            <TableHead>Service Level</TableHead>
            <TableHead>Fill Rate</TableHead>
            <TableHead>Stock Out</TableHead>
            <TableHead>Turnover</TableHead>
            <TableHead>Inventory days</TableHead>
            <TableHead>Biaya kekurangan</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {metrics.map((m) => (
            <TableRow key={`${m.target_type}-${m.scope}-${m.target_id}`}>
              <TableCell>
                <span className="font-medium">{codeOf.get(m.target_id) ?? m.target_id}</span>
                <span className="block text-xs text-muted-foreground">
                  {m.target_type === "material" ? "Material" : "Produk"}
                </span>
              </TableCell>
              <TableCell className="font-medium">{SCOPE_LABEL[m.scope] ?? m.scope}</TableCell>
              <TableCell className="tabular-nums">{pct(m.service_level)}</TableCell>
              <TableCell className="tabular-nums">{pct(m.fill_rate)}</TableCell>
              <TableCell className="tabular-nums">{pct(m.stock_out_rate)}</TableCell>
              <TableCell className="tabular-nums">{turns(m.inventory_turnover)}</TableCell>
              <TableCell className="tabular-nums">
                {m.inventory_days != null ? `${Number(m.inventory_days).toFixed(1)} hari` : "—"}
              </TableCell>
              <TableCell className="tabular-nums">
                {m.shortage_cost != null ? formatMoney(m.shortage_cost) : "—"}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
