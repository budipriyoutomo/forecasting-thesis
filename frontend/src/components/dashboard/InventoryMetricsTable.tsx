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
import type { InventoryMetric } from "@/types/metrics";

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
export function InventoryMetricsTable({ metrics }: { metrics: InventoryMetric[] }) {
  if (metrics.length === 0) {
    return <EmptyState message="Belum ada metrik inventory untuk run ini." />;
  }

  return (
    <div className="overflow-x-auto rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Scope</TableHead>
            <TableHead>Service Level</TableHead>
            <TableHead>Fill Rate</TableHead>
            <TableHead>Stock Out</TableHead>
            <TableHead>Turnover</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {metrics.map((m) => (
            <TableRow key={`${m.scope}-${m.target_id}`}>
              <TableCell className="font-medium">{SCOPE_LABEL[m.scope] ?? m.scope}</TableCell>
              <TableCell className="tabular-nums">{pct(m.service_level)}</TableCell>
              <TableCell className="tabular-nums">{pct(m.fill_rate)}</TableCell>
              <TableCell className="tabular-nums">{pct(m.stock_out_rate)}</TableCell>
              <TableCell className="tabular-nums">{turns(m.inventory_turnover)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
