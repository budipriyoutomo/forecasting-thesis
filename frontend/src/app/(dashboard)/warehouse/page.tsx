"use client";

import { WarehouseConfigForm } from "@/components/warehouse/WarehouseConfigForm";
import { useSetWarehouseConfig, useWarehouseConfig } from "@/hooks/useWarehouse";
import type { WarehouseConfigInput } from "@/types/warehouse";

export default function WarehousePage() {
  const { data: config, isPending, isError } = useWarehouseConfig();
  const save = useSetWarehouseConfig();

  const onSubmit = (input: WarehouseConfigInput) => save.mutate(input);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold">Kapasitas Gudang</h1>
        <p className="text-sm text-muted-foreground">
          Atur luas gudang dan dimensi palet. Dipakai untuk memvalidasi apakah rekomendasi
          inventory muat secara fisik (berbasis palet, tanpa racking).
        </p>
      </div>

      {isPending && <p className="text-sm text-muted-foreground">Memuat konfigurasi…</p>}
      {isError && <p className="text-sm text-destructive">Gagal memuat konfigurasi gudang.</p>}

      {!isPending && (
        <div className="max-w-md rounded-lg border p-4">
          {config === null && (
            <p className="mb-3 text-sm text-muted-foreground">
              Belum ada konfigurasi. Isi form di bawah untuk mengaturnya.
            </p>
          )}
          <WarehouseConfigForm
            initial={config}
            onSubmit={onSubmit}
            submitting={save.isPending}
            error={save.error?.message ?? null}
          />
          {save.isSuccess && (
            <p className="mt-2 text-sm text-green-600 dark:text-green-400">Konfigurasi tersimpan.</p>
          )}
        </div>
      )}
    </div>
  );
}
