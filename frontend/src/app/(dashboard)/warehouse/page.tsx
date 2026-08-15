"use client";

import { PageHeader } from "@/components/common/PageHeader";
import { WarehouseConfigForm } from "@/components/warehouse/WarehouseConfigForm";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useSetWarehouseConfig, useWarehouseConfig } from "@/hooks/useWarehouse";
import type { WarehouseConfigInput } from "@/types/warehouse";

export default function WarehousePage() {
  const { data: config, isPending, isError } = useWarehouseConfig();
  const save = useSetWarehouseConfig();

  const onSubmit = (input: WarehouseConfigInput) => save.mutate(input);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Kapasitas Gudang"
        description="Atur luas gudang dan dimensi palet. Dipakai untuk memvalidasi apakah rekomendasi inventory muat secara fisik (berbasis palet, tanpa racking)."
      />

      {isError && (
        <Alert variant="destructive">
          <AlertDescription>Gagal memuat konfigurasi gudang.</AlertDescription>
        </Alert>
      )}

      <Card className="max-w-lg">
        <CardHeader>
          <CardTitle>Konfigurasi</CardTitle>
          <CardDescription>
            {config === null
              ? "Belum ada konfigurasi. Isi form di bawah untuk mengaturnya."
              : "Perubahan berlaku saat validasi kapasitas dijalankan berikutnya."}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {isPending ? (
            <div className="flex flex-col gap-3" role="status">
              <span className="sr-only">Memuat konfigurasi…</span>
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-2/3" />
            </div>
          ) : (
            <>
              <WarehouseConfigForm
                initial={config}
                onSubmit={onSubmit}
                submitting={save.isPending}
                error={save.error?.message ?? null}
              />
              {/* role=status supaya konfirmasi simpan diumumkan screen reader —
                  perubahannya tidak terlihat kalau fokus masih di tombol. */}
              {save.isSuccess && (
                <p role="status" className="text-sm text-success">
                  Konfigurasi tersimpan.
                </p>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
