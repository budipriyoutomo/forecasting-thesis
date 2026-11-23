"use client";

import { MoreHorizontal, Play, Plus } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { EmptyState } from "@/components/common/EmptyState";
import { FormError } from "@/components/common/FormError";
import { PageHeader } from "@/components/common/PageHeader";
import { TableSkeleton } from "@/components/common/TableSkeleton";
import { CostSummaryCard } from "@/components/dashboard/CostSummaryCard";
import { InventoryMetricsTable } from "@/components/dashboard/InventoryMetricsTable";
import { ReorderTable } from "@/components/dashboard/ReorderTable";
import { ExportMenu } from "@/components/forecast/ExportMenu";
import { ForecastResults } from "@/components/forecast/ForecastResults";
import { MethodSelectionDialog } from "@/components/forecast/MethodSelectionDialog";
import { runLabel } from "@/components/forecast/RunPicker";
import { RunStepper } from "@/components/forecast/RunStepper";
import { ReorderOverrideDialog } from "@/components/override/ReorderOverrideDialog";
import { CapacityAdjustmentPanel } from "@/components/planning/CapacityAdjustmentPanel";
import { InventoryPlanBreakdown } from "@/components/planning/InventoryPlanBreakdown";
import { PlanningSummaryCard } from "@/components/planning/PlanningSummaryCard";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { WarehouseCapacityBadge } from "@/components/warehouse/WarehouseCapacityBadge";
import { useExport } from "@/hooks/useExport";
import {
  useForecastRun,
  useForecastRuns,
  useSelectForecastMethod,
  useSelectForecastMethodForRun,
} from "@/hooks/useForecast";
import { useForecastSettings } from "@/hooks/useForecastSettings";
import { useMaterials } from "@/hooks/useMaterials";
import { useCostSummary, useInventoryMetrics } from "@/hooks/useMetrics";
import { useCan } from "@/hooks/usePermission";
import { useProducts } from "@/hooks/useProducts";
import { useReorderList, useRunPlanning, useStockProjection } from "@/hooks/usePlanning";
import { useGenerateReorder } from "@/hooks/useReorder";
import { useRunWarehouseValidation } from "@/hooks/useWarehouse";
import { type RunStepKey, defaultStep, deriveRunSteps } from "@/lib/runSteps";
import { runStatus } from "@/lib/status";
import type { ReorderRecommendation } from "@/types/reorder";

// CR v3.6 §1/§4 — detail satu forecast run, bisa dibuka ulang (refresh/pindah menu) karena
// seluruhnya dirender dari query (useForecastRun, proyeksi, reorder, biaya), BUKAN dari state
// mutation. Alur = stepper: Forecast → Metode terbaik → Perencanaan → Reorder & biaya.
// 23 Nov 2026: langkah 2 = metode terbaik pilihan sistem (bisa diganti planner); run Fase 11.15
// yang masih PENDING_SELECTION tetap harus dipilih manual.
// Semua role bisa membaca (CR v3.5 §3.2); tombol aksi disembunyikan lewat useCan.
export function RunDetail({ runId, initialStep }: { runId: string; initialStep?: RunStepKey }) {
  const runQuery = useForecastRun(runId);
  const runs = useForecastRuns();
  const { data: products } = useProducts();
  const { data: materials } = useMaterials();
  const { data: settings } = useForecastSettings();
  const projection = useStockProjection(runId);
  const hasPlanning = (projection.data?.length ?? 0) > 0;
  const reorderList = useReorderList(runId);
  const cost = useCostSummary(hasPlanning ? runId : null);
  const inventoryMetrics = useInventoryMetrics(hasPlanning ? runId : null);
  const warehouse = useRunWarehouseValidation(hasPlanning ? runId : null);

  const canSelect = useCan("forecast.select");
  const canPlan = useCan("planning.run");
  const canOverride = useCan("override.create");
  const canRun = useCan("forecast.run");

  const planning = useRunPlanning();
  const reorder = useGenerateReorder();
  const exporter = useExport();
  const selectMethod = useSelectForecastMethod(runId);
  const selectAll = useSelectForecastMethodForRun(runId);
  const [choosing, setChoosing] = useState<{ resultId: string | null; method: string; label: string } | null>(null);
  const [overriding, setOverriding] = useState<{ rec: ReorderRecommendation; label: string } | null>(null);
  // Tautan dashboard bisa membuka langkah tertentu (?step=reorder); default = langkah yang perlu tindakan.
  const [active, setActive] = useState<RunStepKey | null>(initialStep ?? null);

  if (runQuery.isPending) return <TableSkeleton />;
  if (runQuery.isError || !runQuery.data)
    return (
      <EmptyState
        message="Run tidak ditemukan."
        hint={runQuery.error?.message}
        action={
          <Button asChild variant="outline">
            <Link href="/forecast">Kembali ke daftar run</Link>
          </Button>
        }
      />
    );

  const data = runQuery.data;
  const { run } = data;
  const listItem = runs.data?.find((r) => r.run_id === runId);
  const steps = deriveRunSteps({ run, hasPlanning });
  const current = active ?? defaultStep(steps);
  const step = steps.find((s) => s.key === current) ?? steps[0];
  const pending = run.n_pending_selection ?? 0;
  const status = runStatus(run.status);
  const productById = new Map((products ?? []).map((p) => [p.id, p]));
  const nAdjusted = (reorderList.data ?? []).filter((r) => r.adjustment_source).length;

  const selecting = choosing?.resultId ? selectMethod : selectAll;
  const closeChoosing = () => {
    setChoosing(null);
    selectMethod.reset();
    selectAll.reset();
  };
  const onChooseReason = (reason: string) => {
    if (!choosing) return;
    const done = { onSuccess: closeChoosing };
    if (choosing.resultId) selectMethod.mutate({ resultId: choosing.resultId, method: choosing.method, reason }, done);
    else selectAll.mutate({ method: choosing.method, reason }, done);
  };
  const runPlanning = () => planning.mutate({ runId });

  const resultsView = (selectable: boolean) => (
    <ForecastResults
      data={data}
      products={products ?? []}
      displayMetrics={settings?.display_metrics}
      onSelectMethod={
        selectable
          ? (result, method) => {
              const p = productById.get(result.product_id);
              setChoosing({ resultId: result.id, method, label: p ? `${p.code} — ${p.name}` : result.product_id });
            }
          : undefined
      }
      onSelectAll={selectable ? (method) => setChoosing({ resultId: null, method, label: "semua produk di run ini" }) : undefined}
    />
  );

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Detail run"
        description={
          listItem
            ? `${runLabel(listItem)} · horizon ${run.horizon} bulan · ${run.n_products} produk`
            : `Run ${run.run_id.slice(0, 8)} · horizon ${run.horizon} bulan · ${run.n_products} produk`
        }
        actions={
          <>
            <ExportMenu
              runId={runId}
              hasPlanning={hasPlanning}
              pending={exporter.isPending}
              onExport={(input) => exporter.mutate(input)}
            />
            {canRun && (
              <Button asChild>
                <Link href="/forecast/new">
                  <Plus />
                  Forecast baru
                </Link>
              </Button>
            )}
          </>
        }
      />
      <FormError message={exporter.isError ? exporter.error.message : null} />

      <RunStepper steps={steps} active={current} onChange={setActive} />

      {step.status === "locked" && (
        <Alert variant="warning">
          <AlertTitle>Langkah ini belum bisa dikerjakan</AlertTitle>
          <AlertDescription>{step.lockedReason}</AlertDescription>
        </Alert>
      )}

      {current === "forecast" && (
        <section className="flex flex-col gap-4" aria-labelledby="step-forecast">
          <h2 id="step-forecast" className="text-lg font-medium">
            1. Forecast
          </h2>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <Badge variant={status.variant}>{status.label}</Badge>
            <span>
              {run.n_completed} berhasil · {run.n_failed} gagal dari {run.n_products} produk
              {pending > 0 && ` · ${pending} menunggu pemilihan metode`}
            </span>
          </div>
          {resultsView(false)}
          {pending > 0 && (
            <div>
              <Button onClick={() => setActive("select")}>Lanjut: pilih metode untuk {pending} produk</Button>
            </div>
          )}
        </section>
      )}

      {current === "select" && step.status !== "locked" && (
        <section className="flex flex-col gap-4" aria-labelledby="step-select">
          <h2 id="step-select" className="text-lg font-medium">
            2. Metode terbaik
          </h2>
          <p className="text-sm text-muted-foreground">
            Sistem memilih metode terbaik per produk dari pengujian peramalan (prioritas 1) MAD, 2) MAPE, 3) MFE) — buka Detail produk untuk
            melihat analisis kenapa metode itu terbaik. Planner tetap bisa mengganti metode per produk, atau satu metode
            untuk semua produk (alasan wajib).
          </p>
          {!canSelect && (
            <Alert>
              <AlertDescription>Hanya PPIC/Admin yang dapat memilih metode. Anda melihat dalam mode baca.</AlertDescription>
            </Alert>
          )}
          {resultsView(canSelect)}
          {pending === 0 && (
            <div>
              <Button onClick={() => setActive("planning")}>Lanjut: perencanaan</Button>
            </div>
          )}
        </section>
      )}

      {current === "planning" && step.status !== "locked" && (
        <section className="flex flex-col gap-4" aria-labelledby="step-planning">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 id="step-planning" className="text-lg font-medium">
                3. Perencanaan persediaan
              </h2>
              <p className="text-sm text-muted-foreground">
                Satu tombol menjalankan MRP → safety & buffer stock → EOQ → ROP → kapasitas gudang per grup material →
                simulasi stok → evaluasi inventory & biaya. Tiap tab di bawah menampilkan perhitungannya. Stok awal dari
                snapshot ERP terakhir (menu Persediaan Material).
              </p>
            </div>
            {canPlan && (
              <div className="flex items-center gap-2">
                <Button disabled={planning.isPending} onClick={runPlanning}>
                  <Play />
                  {planning.isPending ? "Menjalankan…" : hasPlanning ? "Jalankan ulang perencanaan" : "Jalankan perencanaan"}
                </Button>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="icon" aria-label="Hitung ulang sebagian">
                      <MoreHorizontal />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuLabel>Hitung ulang sebagian</DropdownMenuLabel>
                    <DropdownMenuItem disabled={reorder.isPending} onSelect={() => reorder.mutate({ runId })}>
                      Hitung ulang reorder saja (tanpa proyeksi & biaya)
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            )}
          </div>
          {pending > 0 && (
            <Alert variant="warning">
              <AlertDescription>
                {pending} produk belum dipilih metodenya dan akan dilewati. Pilih metode di langkah 2, lalu jalankan
                perencanaan lagi.
              </AlertDescription>
            </Alert>
          )}
          <FormError message={planning.isError ? planning.error.message : null} />
          <FormError message={reorder.isError ? reorder.error.message : null} />
          {planning.data && <PlanningSummaryCard summary={planning.data} />}
          {(planning.data || nAdjusted > 0) && (
            <CapacityAdjustmentPanel
              runId={runId}
              suggestion={planning.data?.capacity?.suggestion}
              adjustedCount={planning.data?.capacity?.n_adjusted_materials ?? nAdjusted}
              materials={materials ?? []}
              onReplan={runPlanning}
            />
          )}
          {projection.isPending ? (
            <TableSkeleton />
          ) : hasPlanning ? (
            <>
              <InventoryPlanBreakdown
                projection={projection.data ?? []}
                recommendations={reorderList.data ?? []}
                materials={materials ?? []}
              />
              <div>
                <Button variant="outline" onClick={() => setActive("reorder")}>
                  Lanjut: reorder & biaya
                </Button>
              </div>
            </>
          ) : (
            <EmptyState
              message="Perencanaan belum dijalankan untuk run ini."
              hint={canPlan ? "Klik “Jalankan perencanaan”." : "Minta PPIC menjalankan perencanaan."}
            />
          )}
        </section>
      )}

      {current === "reorder" && step.status !== "locked" && (
        <section className="flex flex-col gap-6" aria-labelledby="step-reorder">
          <h2 id="step-reorder" className="text-lg font-medium">
            4. Reorder &amp; biaya
          </h2>
          <div className="flex flex-col gap-3">
            <h3 className="font-medium">Rekomendasi reorder</h3>
            {reorderList.isPending ? (
              <TableSkeleton />
            ) : (
              <ReorderTable
                recommendations={reorderList.data ?? []}
                materials={materials ?? []}
                targetServiceLevel={settings?.service_level_pct}
                onOverride={canOverride ? (rec, label) => setOverriding({ rec, label }) : undefined}
              />
            )}
          </div>

          <div className="flex flex-col gap-3">
            <h3 className="font-medium">Kapasitas gudang produk jadi</h3>
            {warehouse.isPending ? (
              <TableSkeleton />
            ) : warehouse.isError ? (
              <EmptyState message="Kapasitas gudang produk jadi belum bisa dicek." hint={warehouse.error.message} />
            ) : (
              warehouse.data && <WarehouseCapacityBadge validation={warehouse.data} products={products ?? []} />
            )}
          </div>

          <div className="flex flex-col gap-3">
            <h3 className="font-medium">Biaya &amp; kinerja inventory</h3>
            {cost.data && <CostSummaryCard summary={cost.data} />}
            {cost.isError && <FormError message={cost.error.message} />}
            {inventoryMetrics.data && inventoryMetrics.data.length > 0 ? (
              <InventoryMetricsTable
                metrics={inventoryMetrics.data}
                materials={materials ?? []}
                products={products ?? []}
              />
            ) : (
              !inventoryMetrics.isPending && (
                <EmptyState message="Metrik inventory belum tersedia." hint="Jalankan ulang perencanaan untuk menghitungnya." />
              )
            )}
          </div>
        </section>
      )}

      <MethodSelectionDialog
        target={choosing}
        onSubmit={onChooseReason}
        onClose={closeChoosing}
        pending={selecting.isPending}
        error={selecting.error?.message ?? null}
      />
      <ReorderOverrideDialog
        runId={runId}
        recommendation={overriding?.rec ?? null}
        materialLabel={overriding?.label ?? ""}
        onClose={() => setOverriding(null)}
      />
    </div>
  );
}
