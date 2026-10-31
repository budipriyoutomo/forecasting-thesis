"use client";

import { Download, Sparkles } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/components/common/PageHeader";
import { MethodSelector } from "@/components/config/MethodSelector";
import { CostSummaryCard } from "@/components/dashboard/CostSummaryCard";
import { InventoryMetricsTable } from "@/components/dashboard/InventoryMetricsTable";
import { ReorderTable } from "@/components/dashboard/ReorderTable";
import { ForecastResults } from "@/components/forecast/ForecastResults";
import { PlanningSummaryCard } from "@/components/planning/PlanningSummaryCard";
import { StockProjectionTable } from "@/components/planning/StockProjectionTable";
import { FormError } from "@/components/common/FormError";
import { EmptyState } from "@/components/common/EmptyState";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { WarehouseCapacityBadge } from "@/components/warehouse/WarehouseCapacityBadge";
import { useExport } from "@/hooks/useExport";
import { useCreateForecastRun } from "@/hooks/useForecast";
import { useMaterials } from "@/hooks/useMaterials";
import { useCostSummary, useInventoryMetrics } from "@/hooks/useMetrics";
import { useProducts } from "@/hooks/useProducts";
import { useReorderList, useRunPlanning, useStockProjection } from "@/hooks/usePlanning";
import { useGenerateReorder } from "@/hooks/useReorder";
import { useWarehouseValidation } from "@/hooks/useWarehouse";

export default function ForecastConfigPage() {
  const { data: products } = useProducts();
  const { data: materials } = useMaterials();
  const run = useCreateForecastRun();
  const reorder = useGenerateReorder();
  const warehouse = useWarehouseValidation();
  const exporter = useExport();
  const runId = run.data?.run.run_id;

  // Fase 11.8: pipeline tahap 2→4 (reorder → proyeksi stok → evaluasi → biaya) sekali klik.
  const planning = useRunPlanning();
  const planned = Boolean(planning.data) && Boolean(runId);
  const projection = useStockProjection(planned ? (runId as string) : null);
  const reorderList = useReorderList(planned ? (runId as string) : null);
  const recommendations = reorder.data ?? reorderList.data;

  // Biaya & metrik inventory bermakna setelah reorder dihitung (butuh recs persisted).
  const metricsRunId = (reorder.data || planned) && runId ? runId : null;
  const cost = useCostSummary(metricsRunId);
  const inventoryMetrics = useInventoryMetrics(metricsRunId);

  const [selected, setSelected] = useState<string[]>([]);
  const [horizon, setHorizon] = useState(30);
  const [method, setMethod] = useState("");

  const toggle = (id: string) =>
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));

  const onGenerate = () => {
    run.mutate({
      product_ids: selected,
      horizon,
      method: method === "" ? null : method,
    });
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Konfigurasi Forecast"
        description="Pilih produk, horizon, dan metode. Mode otomatis membandingkan seluruh metode aktif lalu memilih yang paling akurat."
      />

      <div className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Pilih produk</CardTitle>
            <CardDescription>
              {selected.length > 0
                ? `${selected.length} produk dipilih.`
                : "Belum ada produk dipilih."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {products && products.length > 0 ? (
              <div className="flex flex-col gap-3">
                {products.map((p) => (
                  <div key={p.id} className="flex items-center gap-3">
                    <Checkbox
                      id={`produk-${p.id}`}
                      checked={selected.includes(p.id)}
                      onCheckedChange={() => toggle(p.id)}
                    />
                    <Label htmlFor={`produk-${p.id}`} className="font-normal">
                      <span className="font-medium">{p.code}</span> — {p.name}
                    </Label>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                message="Belum ada produk."
                hint="Tambah dulu di menu Produk sebelum menjalankan forecast."
              />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Parameter</CardTitle>
            <CardDescription>Berlaku untuk seluruh produk yang dipilih.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <MethodSelector value={method} onChange={setMethod} />

            <div className="flex flex-col gap-2">
              <Label htmlFor="horizon">Horizon (hari)</Label>
              <Input
                id="horizon"
                type="number"
                min={1}
                value={horizon}
                onChange={(e) => setHorizon(Number(e.target.value))}
              />
            </div>

            <FormError message={run.isError ? run.error.message : null} />

            <Button onClick={onGenerate} disabled={selected.length === 0 || run.isPending}>
              <Sparkles />
              {run.isPending ? "Memproses…" : "Generate forecast"}
            </Button>
          </CardContent>
        </Card>
      </div>

      {run.data && runId && (
        <>
          <Separator />

          <section className="flex flex-col gap-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-lg font-medium">Hasil</h2>
              <Button
                variant="outline"
                size="sm"
                disabled={exporter.isPending}
                onClick={() => exporter.mutate({ kind: "forecast", runId })}
              >
                <Download />
                Export forecast (Excel)
              </Button>
            </div>
            <ForecastResults data={run.data} products={products ?? []} />
          </section>

          <section className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 className="text-lg font-medium">Perencanaan Persediaan</h2>
                <p className="text-sm text-muted-foreground">
                  MRP (safety stock, buffer, EOQ) → proyeksi stok & utilisasi gudang material → evaluasi inventory.
                  Stok awal diambil dari snapshot ERP terakhir (menu Persediaan Material).
                </p>
              </div>
              <Button disabled={planning.isPending} onClick={() => planning.mutate({ runId: runId as string })}>
                {planning.isPending ? "Menjalankan…" : "Jalankan perencanaan"}
              </Button>
            </div>
            <FormError message={planning.isError ? planning.error.message : null} />
            {planning.data && <PlanningSummaryCard summary={planning.data} />}
            {projection.data && projection.data.length > 0 && (
              <>
                <div className="flex flex-wrap gap-2">
                  {(["xlsx", "pdf"] as const).map((format) => (
                    <Button
                      key={format}
                      variant="outline"
                      size="sm"
                      disabled={exporter.isPending}
                      onClick={() => exporter.mutate({ kind: "stockProjection", runId, format })}
                    >
                      <Download />
                      Proyeksi stok ({format === "xlsx" ? "Excel" : "PDF"})
                    </Button>
                  ))}
                </div>
                <StockProjectionTable rows={projection.data} materials={materials ?? []} />
              </>
            )}
          </section>

          <section className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-lg font-medium">Rekomendasi Reorder</h2>
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={reorder.isPending}
                  onClick={() => reorder.mutate({ runId })}
                >
                  {reorder.isPending ? "Menghitung…" : "Hitung reorder"}
                </Button>
                {recommendations && (
                  <>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={exporter.isPending}
                      onClick={() => exporter.mutate({ kind: "reorder", runId, format: "xlsx" })}
                    >
                      <Download />
                      Excel
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={exporter.isPending}
                      onClick={() => exporter.mutate({ kind: "reorder", runId, format: "pdf" })}
                    >
                      <Download />
                      PDF
                    </Button>
                  </>
                )}
              </div>
            </div>
            <FormError message={reorder.isError ? reorder.error.message : null} />
            <FormError message={exporter.isError ? exporter.error.message : null} />
            {recommendations && (
              <ReorderTable recommendations={recommendations} materials={materials ?? []} />
            )}
          </section>

          {recommendations && (
            <section className="flex flex-col gap-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-lg font-medium">Kapasitas Gudang Produk Jadi</h2>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={warehouse.isPending}
                  onClick={() => warehouse.mutate(runId)}
                >
                  {warehouse.isPending ? "Memvalidasi…" : "Cek kapasitas"}
                </Button>
              </div>
              <FormError message={warehouse.isError ? warehouse.error.message : null} />
              {warehouse.data && (
                <WarehouseCapacityBadge validation={warehouse.data} products={products ?? []} />
              )}
            </section>
          )}

          {recommendations && (cost.data || inventoryMetrics.data) && (
            <section className="flex flex-col gap-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-lg font-medium">Biaya &amp; Kinerja Inventory</h2>
                {inventoryMetrics.data && (
                  <div className="flex flex-wrap gap-2">
                    {(["xlsx", "pdf"] as const).map((format) => (
                      <Button
                        key={format}
                        variant="outline"
                        size="sm"
                        disabled={exporter.isPending}
                        onClick={() => exporter.mutate({ kind: "metrics", runId, format })}
                      >
                        <Download />
                        Metrik ({format === "xlsx" ? "Excel" : "PDF"})
                      </Button>
                    ))}
                  </div>
                )}
              </div>
              {cost.data && <CostSummaryCard summary={cost.data} />}
              {inventoryMetrics.data && (
                <InventoryMetricsTable
                  metrics={inventoryMetrics.data}
                  materials={materials ?? []}
                  products={products ?? []}
                />
              )}
            </section>
          )}
        </>
      )}
    </div>
  );
}
