"use client";

import Link from "next/link";

import { ExplanationBox } from "@/components/dashboard/ExplanationBox";
import { CandidatesTable } from "@/components/forecast/CandidatesTable";
import { ExogUsage } from "@/components/forecast/ExogUsage";
import { FeatureImportance } from "@/components/forecast/FeatureImportance";
import { ForecastChart } from "@/components/forecast/ForecastChart";
import { ForecastQtyTable } from "@/components/forecast/ForecastQtyTable";
import { MetricValue } from "@/components/forecast/MetricValue";
import { SelectionAnalysis } from "@/components/forecast/SelectionAnalysis";
import {
  FAILURE_FIX,
  forecastTotals,
  productLabel,
  sourceLabel,
} from "@/components/forecast/productResult";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { formatQty } from "@/lib/format";
import { methodLabel } from "@/lib/methods";
import { isPendingResult, resultStatus } from "@/lib/status";
import type { ForecastResult } from "@/types/forecast";
import type { DisplayMetric } from "@/types/forecastSettings";
import type { Product } from "@/types/product";

// CR v3.6 §5 — isi detail satu produk (dulu satu Card penuh per produk di ForecastResults).
// Semua info Card lama tetap ada, dibagi ke tab: Ringkasan · Perbandingan metode · Faktor · Angka.
export function ProductResultDetail({
  result: r,
  product,
  displayMetrics,
  onSelectMethod,
}: {
  result: ForecastResult;
  product?: Product;
  displayMetrics?: DisplayMetric[];
  onSelectMethod?: (result: ForecastResult, method: string) => void;
}) {
  const pending = isPendingResult(r);
  const status = resultStatus(r);
  const totals = forecastTotals(r);
  const source = sourceLabel(r);
  const unit = product?.unit;
  const failed = r.status !== "COMPLETED";

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <Badge variant={status.variant}>{status.label}</Badge>
        {r.method_used && !pending && (
          <span>
            Metode <span className="font-medium">{methodLabel(r.method_used)}</span>
            {source && ` (${source})`}
          </span>
        )}
        {typeof r.hyperparameters?.alpha === "number" && <span>· α {r.hyperparameters.alpha}</span>}
      </div>
      {r.selection_reason && <p className="text-sm text-muted-foreground">Alasan pilihan: {r.selection_reason}</p>}

      {failed && (
        <Alert variant="destructive">
          <AlertTitle>{status.label}</AlertTitle>
          <AlertDescription className="flex flex-col gap-1">
            <span>{r.status_reason ?? "Forecast produk ini gagal dibuat."}</span>
            {FAILURE_FIX[r.status] && <span>{FAILURE_FIX[r.status]}</span>}
            <Link href="/forecast/new" className="font-medium underline underline-offset-4">
              Upload data demand
            </Link>
          </AlertDescription>
        </Alert>
      )}

      {pending && (
        <Alert variant="warning">
          <AlertDescription>
            Metode belum dipilih. Bandingkan metrik tiap metode di tab Perbandingan metode lalu pilih — produk ini
            dilewati di perencanaan sampai metodenya dipilih.
          </AlertDescription>
        </Alert>
      )}

      {totals && (
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-lg border p-3">
            <p className="text-xs text-muted-foreground">Total forecast ({totals.periods} periode)</p>
            <p className="text-lg font-semibold tabular-nums">{formatQty(totals.total, unit)}</p>
          </div>
          <div className="rounded-lg border p-3">
            <p className="text-xs text-muted-foreground">Rata-rata per bulan</p>
            <p className="text-lg font-semibold tabular-nums">{formatQty(totals.average, unit)}</p>
          </div>
          <div className="rounded-lg border p-3">
            <p className="text-xs text-muted-foreground">MAPE metode dipakai</p>
            <MetricValue metric="mape" value={r.mape} />
          </div>
        </div>
      )}

      {!failed && (
        <Tabs defaultValue={pending ? "compare" : "summary"}>
          <TabsList className="flex-wrap">
            <TabsTrigger value="summary">Ringkasan</TabsTrigger>
            <TabsTrigger value="compare">Perbandingan metode</TabsTrigger>
            <TabsTrigger value="factors">Faktor</TabsTrigger>
            <TabsTrigger value="numbers">Angka</TabsTrigger>
          </TabsList>
          <TabsContent value="summary" className="flex flex-col gap-4">
            <SelectionAnalysis analysis={r.selection_analysis} methodUsed={r.method_used} />
            {!r.selection_analysis && <ExplanationBox explanation={r.explanation} />}
            {pending ? (
              <p className="text-sm text-muted-foreground">Grafik tampil setelah metode dipilih.</p>
            ) : (
              <ForecastChart forecast={r.forecast} history={r.history} />
            )}
          </TabsContent>
          <TabsContent value="compare">
            <CandidatesTable
              candidates={r.candidates_evaluated ?? []}
              selectedMethod={pending ? null : r.method_used}
              displayMetrics={displayMetrics ?? ["mad", "mfe", "mape"]}
              defaultOpen
              onSelect={
                onSelectMethod && r.selection_mode !== "manual" ? (method) => onSelectMethod(r, method) : undefined
              }
            />
            {r.selection_analysis?.scope === "global" && (r.selection_analysis.n_products ?? 1) > 1 && (
              <p className="mt-2 text-xs text-muted-foreground">
                Angka di tabel = hasil pengujian produk ini. Peringkat = peringkat rata-rata seluruh{" "}
                {r.selection_analysis.n_products} produk, dasar pemilihan metode terbaik.
              </p>
            )}
            {r.selection_mode === "manual" && (
              <p className="text-sm text-muted-foreground">
                Mode manual — metode dipilih sebelum run, tidak ada perbandingan.
              </p>
            )}
          </TabsContent>
          <TabsContent value="factors" className="flex flex-col gap-4">
            {pending ? (
              <p className="text-sm text-muted-foreground">Faktor tampil setelah metode dipilih.</p>
            ) : (
              <>
                <ExogUsage hyperparameters={r.hyperparameters} />
                <FeatureImportance importance={r.feature_importance ?? null} />
                {!r.hyperparameters && !r.feature_importance && (
                  <p className="text-sm text-muted-foreground">Metode ini tidak memakai variabel eksternal / fitur.</p>
                )}
              </>
            )}
          </TabsContent>
          <TabsContent value="numbers">
            {pending ? (
              <p className="text-sm text-muted-foreground">Angka tampil setelah metode dipilih.</p>
            ) : (
              <ForecastQtyTable forecast={r.forecast} />
            )}
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
}

export function ProductResultSheet({
  result,
  product,
  displayMetrics,
  onSelectMethod,
  onClose,
}: {
  result: ForecastResult | null;
  product?: Product;
  displayMetrics?: DisplayMetric[];
  onSelectMethod?: (result: ForecastResult, method: string) => void;
  onClose: () => void;
}) {
  return (
    <Sheet open={result !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-2xl">
        {result && (
          <>
            <SheetHeader className="mb-4">
              <SheetTitle>{productLabel(result, product)}</SheetTitle>
              <SheetDescription>Detail hasil forecast produk di run ini.</SheetDescription>
            </SheetHeader>
            <ProductResultDetail
              result={result}
              product={product}
              displayMetrics={displayMetrics}
              onSelectMethod={onSelectMethod}
            />
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
