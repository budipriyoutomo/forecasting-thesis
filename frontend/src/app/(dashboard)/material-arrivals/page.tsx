"use client";

import Link from "next/link";
import { useState } from "react";

import { MaterialArrivalsTable } from "@/components/arrivals/MaterialArrivalsTable";
import { EmptyState } from "@/components/common/EmptyState";
import { PageHeader } from "@/components/common/PageHeader";
import { TableSkeleton } from "@/components/common/TableSkeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { useForecastRuns } from "@/hooks/useForecast";
import { useMaterials } from "@/hooks/useMaterials";
import { useReorderList, useStockProjection } from "@/hooks/usePlanning";

function runLabel(createdAt: string | null, runId: string, createdBy?: string | null) {
  const by = createdBy ? ` · oleh ${createdBy}` : "";
  if (!createdAt) return `${runId.slice(0, 8)}${by}`;
  const d = new Date(createdAt);
  return `${d.toLocaleString("id-ID", { dateStyle: "medium", timeStyle: "short" })} · ${runId.slice(0, 8)}${by}`;
}

// Kedatangan material hasil hitungan sistem (20 Nov 2026): pesanan ROP di proyeksi stok
// skenario usulan untuk run terpilih. Read-only — kedatangan tidak lagi diinput/diupload.
export default function MaterialArrivalsPage() {
  const runs = useForecastRuns();
  const [chosen, setChosen] = useState<string | null>(null);
  const runId = chosen ?? runs.data?.[0]?.run_id ?? null;
  const projection = useStockProjection(runId);
  const recs = useReorderList(runId);
  const { data: materials } = useMaterials();

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Kedatangan Material"
        description="Dihitung sistem dari ROP: pesan bila stok sebelum pesan ≤ ROP, qty sesuai kebijakan di Pengaturan Forecast, tiba di periode yang sama."
      />

      {runs.isPending ? (
        <TableSkeleton />
      ) : runs.isError ? (
        <Alert variant="destructive">
          <AlertDescription>{runs.error.message}</AlertDescription>
        </Alert>
      ) : !runs.data?.length ? (
        <EmptyState
          message="Belum ada forecast run."
          hint="Buat forecast lalu jalankan perencanaan untuk menghitung kedatangan material."
          action={
            <Button asChild variant="outline">
              <Link href="/forecast/new">Ke halaman Forecast</Link>
            </Button>
          }
        />
      ) : (
        <>
          <label className="flex w-fit flex-col gap-1 text-sm">
            <span>Forecast run</span>
            <select
              className="h-9 rounded-md border bg-transparent px-3 text-sm"
              value={runId ?? ""}
              onChange={(e) => setChosen(e.target.value)}
            >
              {runs.data.map((r) => (
                <option key={r.run_id} value={r.run_id}>
                  {runLabel(r.created_at, r.run_id, r.created_by)}
                </option>
              ))}
            </select>
          </label>

          {projection.isPending ? (
            <TableSkeleton />
          ) : projection.isError ? (
            <Alert variant="destructive">
              <AlertDescription>{projection.error.message}</AlertDescription>
            </Alert>
          ) : !projection.data?.length ? (
            <EmptyState
              message="Run ini belum punya proyeksi stok."
              hint="Jalankan perencanaan (tahap 2→4) di halaman konfigurasi forecast run ini."
            />
          ) : (
            <MaterialArrivalsTable rows={projection.data} recommendations={recs.data ?? []} materials={materials ?? []} />
          )}
        </>
      )}
    </div>
  );
}
