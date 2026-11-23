"use client";

import { ArrowLeft, Lock, MoreHorizontal, Play, Plus } from "lucide-react";
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
import { StepSection } from "@/components/forecast/StepSection";
import { MethodComparisonView } from "@/components/forecast/method-view/MethodComparisonView";
import { ReorderOverrideDialog } from "@/components/override/ReorderOverrideDialog";
import { CapacityAdjustmentPanel } from "@/components/planning/CapacityAdjustmentPanel";
import { InventoryEvaluation } from "@/components/planning/InventoryEvaluation";
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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

/** CR v3.7 — tampilan langkah 1: per metode (format thesis, default) | per produk (lama). */
export type ForecastView = "method" | "product";
export const FORECAST_VIEWS: ForecastView[] = ["method", "product"];

/** `?view=` disinkronkan tanpa navigasi ulang (param lain, mis. `?step=`, dipertahankan). */
function syncViewParam(view: ForecastView) {
  const url = new URL(window.location.href);
  url.searchParams.set("view", view);
  window.history.replaceState(window.history.state, "", `${url.pathname}${url.search}${url.hash}`);
}

// CR v3.6 §1/§4 — detail satu forecast run, bisa dibuka ulang (refresh/pindah menu) karena
// seluruhnya dirender dari query (useForecastRun, proyeksi, reorder, biaya), BUKAN dari state
// mutation. Alur = stepper: Forecast → Metode terbaik → Perencanaan → Evaluasi inventory → Reorder & gudang
// (langkah Evaluasi disisipkan 23 Nov 2026; biaya & kinerja inventory dipindah ke sana dari langkah Reorder).
// 23 Nov 2026: langkah 2 = metode terbaik pilihan sistem (bisa diganti planner); run Fase 11.15
// yang masih PENDING_SELECTION tetap harus dipilih manual.
// Semua role bisa membaca (CR v3.5 §3.2); tombol aksi disembunyikan lewat useCan.
export function RunDetail({
  runId,
  initialStep,
  initialView,
}: {
  runId: string;
  initialStep?: RunStepKey;
  initialView?: ForecastView;
}) {
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
  const [view, setView] = useState<ForecastView>(initialView ?? "method");
  const changeView = (value: string) => {
    const next = value as ForecastView;
    setView(next);
    syncViewParam(next);
  };

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

  const go = (key: RunStepKey) => {
    setActive(key);
    // Tombol navigasi ada di bawah konten — bawa user kembali ke stepper supaya langkah baru
    // terbaca dari atas.
    document.getElementById("run-steps")?.scrollIntoView?.({ behavior: "smooth", block: "start" });
  };
  const idx = steps.findIndex((s) => s.key === step.key);
  const sectionProps = { index: idx, steps, onNavigate: go };
  const prereq = step.status === "locked" ? steps.slice(0, idx).reverse().find((s) => s.status !== "locked") : undefined;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <Button asChild variant="link" size="sm" className="h-auto w-fit px-0 text-muted-foreground">
          <Link href="/forecast">
            <ArrowLeft />
            Daftar run
          </Link>
        </Button>
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
      </div>
      <FormError message={exporter.isError ? exporter.error.message : null} />

      <div id="run-steps" className="scroll-mt-4">
        <RunStepper steps={steps} active={current} onChange={setActive} />
      </div>

      {step.status === "locked" && (
        <Alert variant="warning">
          <Lock className="size-4" />
          <AlertTitle>Langkah {idx + 1} belum bisa dikerjakan</AlertTitle>
          <AlertDescription className="flex flex-col items-start gap-3">
            <span>{step.lockedReason}</span>
            {prereq && (
              <Button size="sm" variant="outline" onClick={() => go(prereq.key)}>
                <ArrowLeft />
                Buka langkah {steps.indexOf(prereq) + 1}: {prereq.label}
              </Button>
            )}
          </AlertDescription>
        </Alert>
      )}

      {current === "forecast" && (
        <StepSection
          {...sectionProps}
          title="Forecast"
          description="Hasil forecast seluruh metode aktif per varian dan pengujian peramalannya, diakhiri analisis metode terbaik. Tampilan per produk: klik baris produk untuk melihat grafik, metrik pengujian, dan penjelasan."
          nextLabel={pending > 0 ? `Lanjut: pilih metode untuk ${pending} produk` : undefined}
        >
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <Badge variant={status.variant}>{status.label}</Badge>
            <span className="text-muted-foreground">
              <span className="font-medium text-foreground">{run.n_completed}</span> berhasil ·{" "}
              <span className={run.n_failed > 0 ? "font-medium text-destructive" : "font-medium text-foreground"}>
                {run.n_failed}
              </span>{" "}
              gagal dari {run.n_products} produk
              {pending > 0 && ` · ${pending} menunggu pemilihan metode`}
            </span>
          </div>
          <Tabs value={view} onValueChange={changeView}>
            <TabsList>
              <TabsTrigger value="method">Per metode (format thesis)</TabsTrigger>
              <TabsTrigger value="product">Per produk</TabsTrigger>
            </TabsList>
            <TabsContent value="method" className="mt-4">
              <MethodComparisonView runId={runId} products={products ?? []} />
            </TabsContent>
            <TabsContent value="product" className="mt-4">
              {resultsView(false)}
            </TabsContent>
          </Tabs>
        </StepSection>
      )}

      {current === "select" && step.status !== "locked" && (
        <StepSection
          {...sectionProps}
          title="Metode terbaik"
          description={
            <>
              Sistem memilih metode terbaik per produk dari pengujian peramalan (prioritas MAD → MAPE → MFE). Buka
              detail produk untuk melihat analisis alasannya. Planner tetap bisa mengganti metode per produk atau satu
              metode untuk semua produk (alasan wajib).
            </>
          }
        >
          {!canSelect && (
            <Alert>
              <AlertDescription>Hanya PPIC/Admin yang dapat memilih metode. Anda melihat dalam mode baca.</AlertDescription>
            </Alert>
          )}
          {resultsView(canSelect)}
        </StepSection>
      )}

      {current === "planning" && step.status !== "locked" && (
        <StepSection
          {...sectionProps}
          title="Perencanaan persediaan"
          description={
            <>
              Satu tombol menjalankan MRP → safety &amp; buffer stock → EOQ → ROP → kapasitas gudang per grup material →
              simulasi stok → evaluasi inventory &amp; biaya. Stok awal diambil dari snapshot ERP terakhir (menu
              Persediaan Material).
            </>
          }
          actions={
            canPlan && (
              <>
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
                      Hitung ulang reorder saja (tanpa proyeksi &amp; biaya)
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </>
            )
          }
        >
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
            <InventoryPlanBreakdown
              projection={projection.data ?? []}
              recommendations={reorderList.data ?? []}
              materials={materials ?? []}
            />
          ) : (
            <EmptyState
              message="Perencanaan belum dijalankan untuk run ini."
              hint={canPlan ? "Klik “Jalankan perencanaan” di kanan atas langkah ini." : "Minta PPIC menjalankan perencanaan."}
            />
          )}
        </StepSection>
      )}

      {current === "evaluation" && step.status !== "locked" && (
        <StepSection
          {...sectionProps}
          title="Evaluasi usulan inventory"
          description="Kinerja usulan ForecastIQ dibanding kondisi existing (planning perusahaan): fulfilment rate (service level), stockout rate, inventory turnover, holding cost, ordering cost dan shortage cost."
        >
          {cost.isError && <FormError message={cost.error.message} />}
          {inventoryMetrics.isPending ? (
            <TableSkeleton />
          ) : (
            <InventoryEvaluation
              metrics={inventoryMetrics.data ?? []}
              cost={cost.data}
              recommendations={reorderList.data ?? []}
              materials={materials ?? []}
              products={products ?? []}
            />
          )}
          {(cost.data || (inventoryMetrics.data?.length ?? 0) > 0) && (
            <div className="flex flex-col gap-3">
              <h3 className="font-medium">Rincian biaya &amp; metrik per produk / material</h3>
              {cost.data && <CostSummaryCard summary={cost.data} />}
              {inventoryMetrics.data && inventoryMetrics.data.length > 0 && (
                <InventoryMetricsTable
                  metrics={inventoryMetrics.data}
                  materials={materials ?? []}
                  products={products ?? []}
                />
              )}
            </div>
          )}
        </StepSection>
      )}

      {current === "reorder" && step.status !== "locked" && (
        <StepSection
          {...sectionProps}
          title="Reorder & gudang"
          description="Rekomendasi pemesanan material (EOQ & ROP) beserta cek kapasitas gudang produk jadi. Planner bisa mengubah qty rekomendasi dengan alasan."
        >
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
        </StepSection>
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
