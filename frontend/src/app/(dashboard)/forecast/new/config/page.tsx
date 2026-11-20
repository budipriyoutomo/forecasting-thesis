"use client";

import { Sparkles } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { EmptyState } from "@/components/common/EmptyState";
import { FormError } from "@/components/common/FormError";
import { PageHeader } from "@/components/common/PageHeader";
import { PermissionGate } from "@/components/common/PermissionGate";
import { MethodSelector } from "@/components/config/MethodSelector";
import { NewForecastSteps } from "@/components/forecast/NewForecastSteps";
import { ProductPicker } from "@/components/forecast/ProductPicker";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useCreateForecastRun } from "@/hooks/useForecast";
import { useProductDemandCoverage, useProducts } from "@/hooks/useProducts";

// CR v3.5 §3.2: membuat run milik Admin/PPIC — role lain diarahkan ke halaman baca.
// CR v3.6 §1/§4: halaman ini HANYA langkah "Produk & parameter → Generate" di wizard Forecast
// baru. Hasil tidak lagi dirender di sini (dulu hilang saat refresh) — setelah run dibuat,
// planner diarahkan ke /forecast/runs/{id}.
export default function ForecastConfigPage() {
  return (
    <PermissionGate
      action="forecast.run"
      message="Hanya PPIC/Admin yang dapat menjalankan forecast."
      readHref="/forecast"
      readLabel="daftar forecast run"
    >
      <ForecastConfigContent />
    </PermissionGate>
  );
}

function ForecastConfigContent() {
  const router = useRouter();
  const { data: products } = useProducts();
  const { data: coverage } = useProductDemandCoverage();
  const run = useCreateForecastRun();
  const [selected, setSelected] = useState<string[]>([]);
  // Data demand bulanan: horizon = jumlah bulan. 12 = default kolom Kelengkapan variabel eksternal (CR v3.4).
  const [horizon, setHorizon] = useState(12);
  const [method, setMethod] = useState("");

  const onGenerate = () =>
    run.mutate(
      { product_ids: selected, horizon, method: method === "" ? null : method },
      { onSuccess: (data) => router.push(`/forecast/runs/${data.run.run_id}`) },
    );

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Forecast baru"
        description="Pilih produk, horizon, dan metode. Mode otomatis menjalankan seluruh metode aktif berdampingan — planner memilih metode per produk setelah run."
        actions={
          <Button variant="outline" asChild>
            <Link href="/forecast/new">Kembali ke data demand</Link>
          </Button>
        }
      />
      <NewForecastSteps current={run.isPending ? 2 : 1} />

      <div className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Pilih produk</CardTitle>
            <CardDescription>
              {selected.length > 0 ? `${selected.length} produk dipilih.` : "Belum ada produk dipilih."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {products && products.length > 0 ? (
              <ProductPicker products={products} coverage={coverage} selected={selected} onChange={setSelected} />
            ) : (
              <EmptyState message="Belum ada produk." hint="Tambah dulu di menu Produk sebelum menjalankan forecast." />
            )}
          </CardContent>
        </Card>

        <Card className="h-fit">
          <CardHeader>
            <CardTitle className="text-base">Parameter</CardTitle>
            <CardDescription>Berlaku untuk seluruh produk yang dipilih.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <MethodSelector value={method} onChange={setMethod} />

            <div className="flex flex-col gap-2">
              <Label htmlFor="horizon">Horizon (bulan)</Label>
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
    </div>
  );
}
