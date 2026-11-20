"use client";

import Link from "next/link";
import { useState } from "react";

import { MaterialArrivalsTable } from "@/components/arrivals/MaterialArrivalsTable";
import { EmptyState } from "@/components/common/EmptyState";
import { PageHeader } from "@/components/common/PageHeader";
import { TableSkeleton } from "@/components/common/TableSkeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RunPicker } from "@/components/forecast/RunPicker";
import { Button } from "@/components/ui/button";
import { useForecastRuns } from "@/hooks/useForecast";
import { useMaterials } from "@/hooks/useMaterials";
import { useReorderList, useStockProjection } from "@/hooks/usePlanning";

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
              <Link href="/forecast">Ke halaman Forecast</Link>
            </Button>
          }
        />
      ) : (
        <>
          <div className="flex flex-wrap items-end gap-3">
            <RunPicker runs={runs.data} value={runId} onChange={setChosen} />
            {runId && (
              <Button asChild variant="outline" size="sm">
                <Link href={`/forecast/runs/${runId}`}>Lihat detail run</Link>
              </Button>
            )}
          </div>

          {projection.isPending ? (
            <TableSkeleton />
          ) : projection.isError ? (
            <Alert variant="destructive">
              <AlertDescription>{projection.error.message}</AlertDescription>
            </Alert>
          ) : !projection.data?.length ? (
            <EmptyState
              message="Run ini belum punya proyeksi stok."
              hint="Jalankan perencanaan (langkah 3) di halaman detail run ini."
            />
          ) : (
            <MaterialArrivalsTable rows={projection.data} recommendations={recs.data ?? []} materials={materials ?? []} />
          )}
        </>
      )}
    </div>
  );
}
