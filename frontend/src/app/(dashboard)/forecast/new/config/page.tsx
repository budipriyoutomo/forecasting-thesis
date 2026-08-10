"use client";

import { useState } from "react";

import { MethodSelector } from "@/components/config/MethodSelector";
import { CostSummaryCard } from "@/components/dashboard/CostSummaryCard";
import { InventoryMetricsTable } from "@/components/dashboard/InventoryMetricsTable";
import { ReorderTable } from "@/components/dashboard/ReorderTable";
import { ForecastResults } from "@/components/forecast/ForecastResults";
import { MaterialRequirementsTable } from "@/components/forecast/MaterialRequirementsTable";
import { Button } from "@/components/ui/button";
import { useExport } from "@/hooks/useExport";
import { WarehouseCapacityBadge } from "@/components/warehouse/WarehouseCapacityBadge";
import { useCreateForecastRun, useMaterialRequirements } from "@/hooks/useForecast";
import { useCostSummary, useInventoryMetrics } from "@/hooks/useMetrics";
import { useProducts } from "@/hooks/useProducts";
import { useGenerateReorder } from "@/hooks/useReorder";
import { useWarehouseValidation } from "@/hooks/useWarehouse";

export default function ForecastConfigPage() {
  const { data: products } = useProducts();
  const run = useCreateForecastRun();
  const reorder = useGenerateReorder();
  const warehouse = useWarehouseValidation();
  const exporter = useExport();
  const runId = run.data?.run.run_id;
  // Kebutuhan material tersedia langsung setelah run (breakdown BOM jalan di create_run).
  const requirements = useMaterialRequirements(runId ?? null);

  // Biaya & metrik inventory bermakna setelah reorder dihitung (butuh recs persisted).
  const metricsRunId = reorder.data && runId ? runId : null;
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
      <h1 className="text-2xl font-semibold">Konfigurasi Forecast</h1>

      <section className="flex flex-col gap-2">
        <h2 className="text-sm font-medium">Pilih produk</h2>
        <div className="flex flex-col gap-1">
          {(products ?? []).map((p) => (
            <label key={p.id} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={selected.includes(p.id)}
                onChange={() => toggle(p.id)}
              />
              {p.code} — {p.name}
            </label>
          ))}
          {(!products || products.length === 0) && (
            <p className="text-sm text-muted-foreground">Belum ada produk. Tambah dulu di menu Produk.</p>
          )}
        </div>
      </section>

      <div className="flex max-w-md flex-col gap-3">
        <MethodSelector value={method} onChange={setMethod} />
        <div className="flex flex-col gap-1">
          <label htmlFor="horizon" className="text-sm font-medium">
            Horizon (hari)
          </label>
          <input
            id="horizon"
            type="number"
            min={1}
            className="h-10 rounded-md border border-input bg-background px-3 text-sm"
            value={horizon}
            onChange={(e) => setHorizon(Number(e.target.value))}
          />
        </div>

        {run.isError && <p className="text-sm text-destructive">{run.error.message}</p>}

        <Button onClick={onGenerate} disabled={selected.length === 0 || run.isPending}>
          {run.isPending ? "Memproses…" : "Generate forecast"}
        </Button>
      </div>

      {run.data && runId && (
        <>
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-medium">Hasil</h2>
            <Button
              variant="outline"
              size="sm"
              disabled={exporter.isPending}
              onClick={() => exporter.mutate({ kind: "forecast", runId })}
            >
              Export forecast (Excel)
            </Button>
          </div>
          <ForecastResults data={run.data} />

          <section className="flex flex-col gap-2">
            <h2 className="text-lg font-medium">Kebutuhan Material (BOM)</h2>
            {requirements.isError && (
              <p className="text-sm text-destructive">{requirements.error.message}</p>
            )}
            {requirements.data && <MaterialRequirementsTable requirements={requirements.data} />}
          </section>

          <section className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-medium">Rekomendasi Reorder</h2>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={reorder.isPending}
                  onClick={() => reorder.mutate({ runId })}
                >
                  {reorder.isPending ? "Menghitung…" : "Hitung reorder"}
                </Button>
                {reorder.data && (
                  <>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={exporter.isPending}
                      onClick={() => exporter.mutate({ kind: "reorder", runId, format: "xlsx" })}
                    >
                      Excel
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={exporter.isPending}
                      onClick={() => exporter.mutate({ kind: "reorder", runId, format: "pdf" })}
                    >
                      PDF
                    </Button>
                  </>
                )}
              </div>
            </div>
            {reorder.isError && <p className="text-sm text-destructive">{reorder.error.message}</p>}
            {exporter.isError && <p className="text-sm text-destructive">{exporter.error.message}</p>}
            {reorder.data && <ReorderTable recommendations={reorder.data} />}
          </section>

          {reorder.data && (
            <section className="flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-medium">Kapasitas Gudang</h2>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={warehouse.isPending}
                  onClick={() => warehouse.mutate(runId)}
                >
                  {warehouse.isPending ? "Memvalidasi…" : "Cek kapasitas"}
                </Button>
              </div>
              {warehouse.isError && <p className="text-sm text-destructive">{warehouse.error.message}</p>}
              {warehouse.data && <WarehouseCapacityBadge validation={warehouse.data} />}
            </section>
          )}

          {reorder.data && (cost.data || inventoryMetrics.data) && (
            <section className="flex flex-col gap-4">
              <h2 className="text-lg font-medium">Biaya & Kinerja Inventory</h2>
              {cost.data && <CostSummaryCard summary={cost.data} />}
              {inventoryMetrics.data && <InventoryMetricsTable metrics={inventoryMetrics.data} />}
            </section>
          )}
        </>
      )}
    </div>
  );
}
