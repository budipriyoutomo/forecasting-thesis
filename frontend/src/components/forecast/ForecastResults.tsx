"use client";

import { useState } from "react";

import { ExplanationBox } from "@/components/dashboard/ExplanationBox";
import { CandidatesTable } from "@/components/forecast/CandidatesTable";
import { FeatureImportance } from "@/components/forecast/FeatureImportance";
import { ForecastChart } from "@/components/forecast/ForecastChart";
import { ForecastQtyTable } from "@/components/forecast/ForecastQtyTable";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatNumber } from "@/lib/format";
import { mapeLabel } from "@/lib/mape";
import type { ForecastResult, ForecastRunResponse } from "@/types/forecast";
import type { DisplayMetric } from "@/types/forecastSettings";
import type { Product } from "@/types/product";

const STATUS_LABEL: Record<string, string> = {
  COMPLETED: "Selesai",
  INSUFFICIENT_DATA: "Data kurang",
  MODEL_SELECTION_FAILED: "Semua metode gagal",
};

const ALL_METRICS: DisplayMetric[] = ["mad", "mfe", "mse", "mape"];

function isPending(r: ForecastResult): boolean {
  return r.status === "COMPLETED" && r.selection_status === "PENDING_SELECTION";
}

function sourceLabel(r: ForecastResult): string {
  if (r.selection_mode === "manual") return "dipilih manual sebelum run";
  if (r.selection_reason) return "dipilih planner";
  return "hasil run lama"; // pemenang otomatis sebelum Fase 11.15
}

// Fase 11.15 — tidak ada metode pemenang. Mode otomatis menjalankan semua metode aktif;
// planner memilih metode per produk (onSelectMethod) atau satu metode untuk semua produk
// (onSelectAll). Produk yang belum dipilih dilewati di perencanaan persediaan.
// `products` opsional: bila diberikan, judul kartu memakai "kode — nama" alih-alih UUID.
export function ForecastResults({
  data,
  products = [],
  displayMetrics = ALL_METRICS,
  onSelectMethod,
  onSelectAll,
}: {
  data: ForecastRunResponse;
  products?: Product[];
  displayMetrics?: DisplayMetric[];
  onSelectMethod?: (result: ForecastResult, method: string) => void;
  onSelectAll?: (method: string) => void;
}) {
  const { run, results } = data;
  const productById = new Map(products.map((p) => [p.id, p]));
  const nPending = run.n_pending_selection ?? results.filter(isPending).length;
  // Metode yang bisa dipilih di minimal satu produk (punya deret forecast).
  const bulkMethods = [
    ...new Set(
      results.flatMap((r) =>
        r.status === "COMPLETED"
          ? (r.candidates_evaluated ?? []).filter((c) => c.forecast?.length).map((c) => c.method)
          : [],
      ),
    ),
  ].sort();
  const [bulkMethod, setBulkMethod] = useState("");

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <Badge variant={run.status === "COMPLETED" ? "secondary" : "outline"}>{run.status}</Badge>
        <span>
          {run.n_completed} berhasil · {run.n_failed} gagal dari {run.n_products} produk.
        </span>
      </div>

      {nPending > 0 && (
        <Alert>
          <AlertDescription>
            {nPending} produk menunggu pemilihan metode. Sistem tidak memilih metode otomatis —
            bandingkan metrik tiap metode lalu pilih. Produk yang belum dipilih dilewati di
            perencanaan persediaan.
          </AlertDescription>
        </Alert>
      )}

      {onSelectAll && bulkMethods.length > 0 && (
        <div className="flex flex-wrap items-end gap-2">
          <label className="flex flex-col gap-1 text-sm">
            <span>Metode untuk semua produk</span>
            <select
              className="h-9 rounded-md border bg-transparent px-3 text-sm"
              value={bulkMethod}
              onChange={(e) => setBulkMethod(e.target.value)}
            >
              <option value="">Pilih metode…</option>
              {bulkMethods.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </label>
          <Button variant="outline" disabled={!bulkMethod} onClick={() => onSelectAll(bulkMethod)}>
            Pakai untuk semua produk
          </Button>
        </div>
      )}

      <div className="flex flex-col gap-4">
        {results.map((r) => {
          const product = productById.get(r.product_id);
          const pending = isPending(r);
          return (
            <Card key={r.id ?? r.product_id}>
              <CardHeader>
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="flex flex-col gap-1">
                    <CardTitle className="text-base">
                      {product ? `${product.code} — ${product.name}` : r.product_id}
                    </CardTitle>
                    {r.status === "COMPLETED" && !pending && (
                      <CardDescription>
                        Metode <span className="font-medium">{r.method_used}</span> ({sourceLabel(r)})
                        {r.mape != null && (
                          <>
                            {" "}
                            · MAPE {formatNumber(r.mape)}% ({mapeLabel(r.mape)})
                          </>
                        )}
                        {typeof r.hyperparameters?.alpha === "number" && <> · α {r.hyperparameters.alpha}</>}
                        {r.selection_reason && <> · Alasan: {r.selection_reason}</>}
                      </CardDescription>
                    )}
                    {pending && <CardDescription>Metode belum dipilih.</CardDescription>}
                  </div>
                  <Badge variant={r.status !== "COMPLETED" ? "destructive" : pending ? "outline" : "secondary"}>
                    {pending ? "Metode belum dipilih" : (STATUS_LABEL[r.status] ?? r.status)}
                  </Badge>
                </div>
              </CardHeader>

              {r.status === "COMPLETED" && (
                <CardContent className="flex flex-col gap-4">
                  <ExplanationBox explanation={r.explanation} />
                  <CandidatesTable
                    candidates={r.candidates_evaluated ?? []}
                    selectedMethod={pending ? null : r.method_used}
                    displayMetrics={displayMetrics}
                    onSelect={
                      onSelectMethod && r.selection_mode !== "manual"
                        ? (method) => onSelectMethod(r, method)
                        : undefined
                    }
                  />
                  {!pending && (
                    <>
                      <FeatureImportance importance={r.feature_importance ?? null} />
                      <ForecastChart forecast={r.forecast} />
                      <ForecastQtyTable forecast={r.forecast} />
                    </>
                  )}
                </CardContent>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}
