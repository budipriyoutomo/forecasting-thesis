"use client";

import { Plus } from "lucide-react";
import Link from "next/link";

import { EmptyState } from "@/components/common/EmptyState";
import { PageHeader } from "@/components/common/PageHeader";
import { TableSkeleton } from "@/components/common/TableSkeleton";
import { RunsTable } from "@/components/forecast/RunsTable";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { useForecastRuns } from "@/hooks/useForecast";
import { useCan } from "@/hooks/usePermission";

// CR v3.6 §1 — /forecast: daftar run. Hasil run selalu bisa dibuka ulang di detail run.
export default function ForecastRunsPage() {
  const runs = useForecastRuns();
  const canRun = useCan("forecast.run");

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Forecast"
        description="Daftar forecast run. Buka run untuk memilih metode, menjalankan perencanaan, dan melihat reorder & biaya."
        actions={
          canRun && (
            <Button asChild>
              <Link href="/forecast/new">
                <Plus />
                Forecast baru
              </Link>
            </Button>
          )
        }
      />
      {runs.isPending ? (
        <TableSkeleton />
      ) : runs.isError ? (
        <Alert variant="destructive">
          <AlertDescription>{runs.error.message}</AlertDescription>
        </Alert>
      ) : runs.data.length === 0 ? (
        <EmptyState
          message="Belum ada forecast run."
          hint={canRun ? "Mulai dari tombol “Forecast baru”." : "Run dibuat oleh PPIC/Admin."}
        />
      ) : (
        <RunsTable runs={runs.data} />
      )}
    </div>
  );
}
