"use client";

import type { ColumnDef } from "@tanstack/react-table";
import Link from "next/link";
import { useMemo } from "react";

import { DataTable } from "@/components/common/DataTable";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDateTime } from "@/lib/format";
import { runStatus } from "@/lib/status";
import type { ForecastRunListItem } from "@/types/forecast";

// CR v3.6 §1 — daftar run (semua role, terbaru dulu).
export function RunsTable({ runs }: { runs: ForecastRunListItem[] }) {
  const columns = useMemo<ColumnDef<ForecastRunListItem>[]>(
    () => [
      {
        accessorKey: "created_at",
        header: "Tanggal",
        cell: ({ row }) => <span className="whitespace-nowrap">{formatDateTime(row.original.created_at)}</span>,
      },
      { accessorKey: "created_by", header: "Dibuat oleh", cell: ({ row }) => row.original.created_by ?? "—" },
      {
        accessorKey: "horizon",
        header: "Horizon",
        cell: ({ row }) => <span className="tabular-nums">{row.original.horizon} bulan</span>,
      },
      {
        accessorKey: "n_products",
        header: "Produk",
        cell: ({ row }) => {
          const r = row.original;
          if (r.n_products == null) return "—";
          return (
            <span className="flex flex-col tabular-nums">
              {r.n_products}
              <span className="text-xs text-muted-foreground">
                {r.n_completed ?? 0} berhasil · {r.n_failed ?? 0} gagal
              </span>
            </span>
          );
        },
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ row }) => {
          const s = runStatus(row.original.status);
          return <Badge variant={s.variant}>{s.label}</Badge>;
        },
      },
      {
        accessorKey: "n_pending_selection",
        header: "Pemilihan metode",
        cell: ({ row }) => {
          const n = row.original.n_pending_selection;
          if (n == null) return "—";
          return n > 0 ? <Badge variant="warning">{n} belum dipilih</Badge> : <span className="text-sm">Lengkap</span>;
        },
      },
      {
        accessorKey: "has_planning",
        header: "Perencanaan",
        cell: ({ row }) =>
          row.original.has_planning ? (
            <Badge variant="success">Sudah</Badge>
          ) : (
            <span className="text-sm text-muted-foreground">Belum</span>
          ),
      },
      {
        id: "actions",
        header: "Aksi",
        enableSorting: false,
        cell: ({ row }) => (
          <Button asChild size="sm" variant="outline">
            <Link href={`/forecast/runs/${row.original.run_id}`} aria-label={`Buka run ${row.original.run_id.slice(0, 8)}`}>
              Buka
            </Link>
          </Button>
        ),
      },
    ],
    [],
  );

  return <DataTable columns={columns} data={runs} pageSize={20} emptyMessage="Belum ada forecast run." />;
}
