"use client";

import type { ColumnDef } from "@tanstack/react-table";
import { useMemo, useState } from "react";

import { DataTable } from "@/components/common/DataTable";
import { MetricHeader } from "@/components/forecast/MetricHeader";
import { MetricValue } from "@/components/forecast/MetricValue";
import { appliedMetric, forecastTotals, productLabel, sourceLabel } from "@/components/forecast/productResult";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatQty } from "@/lib/format";
import { methodLabel } from "@/lib/methods";
import { isPendingResult, resultStatus } from "@/lib/status";
import type { ForecastResult } from "@/types/forecast";
import type { Product } from "@/types/product";

export type ResultFilter = "all" | "done" | "pending" | "failed";

const FILTER_LABEL: Record<ResultFilter, string> = {
  all: "Semua",
  done: "Selesai",
  pending: "Belum dipilih",
  failed: "Gagal",
};

export function matchesFilter(r: ForecastResult, filter: ResultFilter): boolean {
  if (filter === "all") return true;
  if (filter === "failed") return r.status !== "COMPLETED";
  if (filter === "pending") return isPendingResult(r);
  return r.status === "COMPLETED" && !isPendingResult(r);
}

interface Row {
  result: ForecastResult;
  code: string;
  name: string;
  unit?: string;
  statusLabel: string;
  method: string;
  mad: number | null;
  mfe: number | null;
  mape: number | null;
  total: number | null;
  average: number | null;
  source: string;
}

// CR v3.6 §5 — tabel ringkasan produk (metrik: MAD, MFE, MAPE — 21 Nov 2026) (pengganti satu Card penuh per produk): 50 produk
// tetap bisa discan satu layar. Klik "Detail" → Sheet (ProductResultSheet).
export function ProductResultsTable({
  results,
  products = [],
  onOpen,
}: {
  results: ForecastResult[];
  products?: Product[];
  onOpen: (result: ForecastResult) => void;
}) {
  const [filter, setFilter] = useState<ResultFilter>("all");

  const counts = useMemo(
    () =>
      Object.fromEntries(
        (Object.keys(FILTER_LABEL) as ResultFilter[]).map((f) => [f, results.filter((r) => matchesFilter(r, f)).length]),
      ) as Record<ResultFilter, number>,
    [results],
  );

  const rows = useMemo<Row[]>(() => {
    const byId = new Map(products.map((p) => [p.id, p]));
    return results
      .filter((r) => matchesFilter(r, filter))
      .map((r) => {
        const p = byId.get(r.product_id);
        const totals = forecastTotals(r);
        return {
          result: r,
          code: p?.code ?? r.product_id,
          name: p?.name ?? (p ? "" : productLabel(r)),
          unit: p?.unit,
          statusLabel: resultStatus(r).label,
          method: r.method_used && !isPendingResult(r) ? methodLabel(r.method_used) : "—",
          mad: appliedMetric(r, "mad"),
          mfe: appliedMetric(r, "mfe"),
          mape: appliedMetric(r, "mape"),
          total: totals?.total ?? null,
          average: totals?.average ?? null,
          source: sourceLabel(r) ?? "—",
        };
      });
  }, [results, products, filter]);

  const columns = useMemo<ColumnDef<Row>[]>(
    () => [
      {
        id: "search",
        accessorFn: (r) => `${r.code} ${r.name}`,
        header: "Kode",
        cell: ({ row }) => <span className="font-medium">{row.original.code}</span>,
      },
      { accessorKey: "name", header: "Nama" },
      {
        accessorKey: "statusLabel",
        header: "Status",
        cell: ({ row }) => {
          const s = resultStatus(row.original.result);
          return <Badge variant={s.variant}>{s.label}</Badge>;
        },
      },
      { accessorKey: "method", header: "Metode dipakai" },
      {
        accessorKey: "mad",
        header: () => <MetricHeader metric="mad" />,
        cell: ({ row }) => <MetricValue metric="mad" value={row.original.mad} />,
      },
      {
        accessorKey: "mfe",
        header: () => <MetricHeader metric="mfe" />,
        cell: ({ row }) => <MetricValue metric="mfe" value={row.original.mfe} />,
      },
      {
        accessorKey: "mape",
        header: () => <MetricHeader metric="mape" />,
        cell: ({ row }) => <MetricValue metric="mape" value={row.original.mape} />,
      },
      {
        accessorKey: "total",
        header: "Total forecast",
        cell: ({ row }) => (
          <span className="flex flex-col tabular-nums">
            {formatQty(row.original.total, row.original.unit)}
            {row.original.average != null && (
              <span className="text-xs text-muted-foreground">
                rata-rata {formatQty(row.original.average, row.original.unit)}/bln
              </span>
            )}
          </span>
        ),
      },
      { accessorKey: "source", header: "Sumber pilihan" },
      {
        id: "actions",
        header: "Aksi",
        enableSorting: false,
        cell: ({ row }) => (
          <Button
            size="sm"
            variant={isPendingResult(row.original.result) ? "default" : "outline"}
            aria-label={`Detail ${row.original.code}`}
            onClick={() => onOpen(row.original.result)}
          >
            {isPendingResult(row.original.result) ? "Pilih metode" : "Detail"}
          </Button>
        ),
      },
    ],
    [onOpen],
  );

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-2" role="group" aria-label="Filter status produk">
        {(Object.keys(FILTER_LABEL) as ResultFilter[]).map((f) => (
          <Button
            key={f}
            size="sm"
            variant={filter === f ? "default" : "outline"}
            aria-pressed={filter === f}
            onClick={() => setFilter(f)}
          >
            {FILTER_LABEL[f]} ({counts[f]})
          </Button>
        ))}
      </div>
      <DataTable
        columns={columns}
        data={rows}
        searchColumn="search"
        searchPlaceholder="Cari kode / nama produk…"
        pageSize={50}
        emptyMessage="Tidak ada produk untuk filter ini."
      />
    </div>
  );
}
