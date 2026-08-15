"use client";

import type { ColumnDef } from "@tanstack/react-table";
import { useMemo } from "react";

import { DataTable } from "@/components/common/DataTable";
import { TableSkeleton } from "@/components/common/TableSkeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { formatDate, formatNumber } from "@/lib/format";
import { useUploadHistory } from "@/hooks/useUploads";
import type { UploadSessionSummary } from "@/types/upload";

export function UploadHistory() {
  const { data, isPending, isError } = useUploadHistory();

  const columns = useMemo<ColumnDef<UploadSessionSummary>[]>(
    () => [
      {
        accessorKey: "file_name",
        header: "File",
        cell: ({ row }) => <span className="font-medium">{row.original.file_name}</span>,
      },
      {
        accessorKey: "created_at",
        header: "Diunggah",
        cell: ({ row }) => formatDate(row.original.created_at),
      },
      {
        accessorKey: "n_rows",
        header: "Baris",
        cell: ({ row }) => (
          <span className="tabular-nums">{formatNumber(row.original.n_rows)}</span>
        ),
      },
      {
        accessorKey: "n_products_detected",
        header: "Produk",
        cell: ({ row }) => (
          <span className="tabular-nums">{formatNumber(row.original.n_products_detected)}</span>
        ),
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ row }) => (
          <Badge variant={row.original.status === "validated" ? "secondary" : "outline"}>
            {row.original.status}
          </Badge>
        ),
      },
    ],
    [],
  );

  if (isPending) return <TableSkeleton columns={5} rows={3} />;
  if (isError) {
    return (
      <Alert variant="destructive">
        <AlertDescription>Gagal memuat riwayat upload.</AlertDescription>
      </Alert>
    );
  }

  return (
    <DataTable
      columns={columns}
      data={data ?? []}
      pageSize={5}
      emptyMessage="Belum ada upload."
    />
  );
}
