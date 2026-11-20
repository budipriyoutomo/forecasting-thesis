"use client";

import { useState } from "react";

import { ProductResultSheet } from "@/components/forecast/ProductResultSheet";
import { ProductResultsTable } from "@/components/forecast/ProductResultsTable";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { methodLabel } from "@/lib/methods";
import { isPendingResult } from "@/lib/status";
import type { ForecastResult, ForecastRunResponse } from "@/types/forecast";
import type { DisplayMetric } from "@/types/forecastSettings";
import type { Product } from "@/types/product";

// Fase 11.15 — tidak ada metode pemenang. Mode otomatis menjalankan semua metode aktif;
// planner memilih metode per produk (onSelectMethod) atau satu metode untuk semua produk
// (onSelectAll). Produk yang belum dipilih dilewati di perencanaan persediaan.
// CR v3.6 §5 — tampilan: tabel ringkasan produk + Sheet detail per produk (bukan satu Card
// panjang per produk). Logika pemilihan metode tidak berubah.
export function ForecastResults({
  data,
  products = [],
  displayMetrics,
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
  const nPending = run.n_pending_selection ?? results.filter(isPendingResult).length;
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
  // Simpan id, bukan objek: setelah memilih metode data run di-refetch dan Sheet harus
  // menampilkan hasil terbaru.
  const [openId, setOpenId] = useState<string | null>(null);
  const open = results.find((r) => (r.id ?? r.product_id) === openId) ?? null;

  return (
    <div className="flex flex-col gap-4">
      {nPending > 0 && (
        <Alert variant="warning">
          <AlertDescription>
            {nPending} produk menunggu pemilihan metode. Sistem tidak memilih metode otomatis — bandingkan metrik
            tiap metode lalu pilih. Produk yang belum dipilih dilewati di perencanaan persediaan.
          </AlertDescription>
        </Alert>
      )}

      {onSelectAll && bulkMethods.length > 0 && (
        <div className="flex flex-wrap items-end gap-2">
          <div className="flex w-64 flex-col gap-1">
            <Label htmlFor="bulk-method">Metode untuk semua produk</Label>
            <Select value={bulkMethod || undefined} onValueChange={setBulkMethod}>
              <SelectTrigger id="bulk-method">
                <SelectValue placeholder="Pilih metode…" />
              </SelectTrigger>
              <SelectContent>
                {bulkMethods.map((m) => (
                  <SelectItem key={m} value={m}>
                    {methodLabel(m)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button variant="outline" disabled={!bulkMethod} onClick={() => onSelectAll(bulkMethod)}>
            Pakai untuk semua produk
          </Button>
        </div>
      )}

      <ProductResultsTable
        results={results}
        products={products}
        onOpen={(r) => setOpenId(r.id ?? r.product_id)}
      />

      <ProductResultSheet
        result={open}
        product={open ? productById.get(open.product_id) : undefined}
        displayMetrics={displayMetrics}
        onSelectMethod={onSelectMethod}
        onClose={() => setOpenId(null)}
      />
    </div>
  );
}
