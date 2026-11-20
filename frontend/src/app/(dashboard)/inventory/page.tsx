"use client";

import { toast } from "sonner";

import { ImportButton } from "@/components/common/ImportButton";
import { PageHeader } from "@/components/common/PageHeader";
import { TableSkeleton } from "@/components/common/TableSkeleton";
import { LatestStockTable } from "@/components/inventory/LatestStockTable";
import { WasteFactorTable } from "@/components/inventory/WasteFactorTable";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useImportSnapshots, useImportUsage, useLatestStock, useWasteFactors } from "@/hooks/useInventory";
import { useMaterials } from "@/hooks/useMaterials";

// Data input tahap 3–4 thesis (Fase 11.1/11.5): stok awal dari ERP dan pemakaian aktual (dasar
// buffer stock / faktor waste). Kedatangan bukan input lagi (20 Nov 2026): dihitung sistem dari ROP
// dan ditampilkan di halaman Kedatangan Material (/material-arrivals).
export default function InventoryPage() {
  const { data: materials } = useMaterials();
  const latest = useLatestStock();
  const waste = useWasteFactors();
  const importSnapshots = useImportSnapshots();
  const importUsage = useImportUsage();

  const imported = { onSuccess: (r: { imported: number }) => toast.success(`${r.imported} baris diimpor`), onError: (e: Error) => toast.error(e.message) };
  const list = materials ?? [];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Persediaan Material"
        description="Stok awal dari ERP dan pemakaian aktual material — input proyeksi stok, utilisasi gudang, dan buffer stock. Kedatangan material dihitung sistem dari ROP."
      />
      <Tabs defaultValue="stock">
        <TabsList>
          <TabsTrigger value="stock">Stok ERP</TabsTrigger>
          <TabsTrigger value="usage">Pemakaian aktual</TabsTrigger>
        </TabsList>

        <TabsContent value="stock" className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm text-muted-foreground">
              Kolom: <code>material_code</code>, <code>snapshot_date</code>, <code>qty</code> [, <code>uom</code>]. Tanggal sama ditimpa.
            </p>
            <ImportButton label="Import stok ERP" pending={importSnapshots.isPending} onFile={(f) => importSnapshots.mutate(f, imported)} />
          </div>
          {latest.isPending ? <TableSkeleton /> : <LatestStockTable latest={latest.data ?? []} materials={list} />}
        </TabsContent>

        <TabsContent value="usage" className="flex flex-col gap-4">
          <Alert>
            <AlertDescription>
              Kolom: <code>material_code</code>, <code>period</code>, <code>actual_usage</code>, dan{" "}
              <code>standard_usage</code> — atau <code>product_code</code> + <code>production_output</code> (standar = output × BOM).
              Buffer = max(0, Σaktual ÷ Σstandar − 1) × kebutuhan periode.
            </AlertDescription>
          </Alert>
          <div>
            <ImportButton label="Import pemakaian" pending={importUsage.isPending} onFile={(f) => importUsage.mutate(f, imported)} />
          </div>
          {waste.isPending ? <TableSkeleton /> : <WasteFactorTable factors={waste.data ?? []} materials={list} />}
        </TabsContent>
      </Tabs>
    </div>
  );
}
