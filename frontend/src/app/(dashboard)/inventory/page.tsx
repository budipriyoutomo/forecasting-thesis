"use client";

import { useId, useState, type ReactNode } from "react";
import { toast } from "sonner";

import { ImportButton } from "@/components/common/ImportButton";
import { ImportTemplateCard } from "@/components/common/ImportTemplateCard";
import { PageHeader } from "@/components/common/PageHeader";
import { TableSkeleton } from "@/components/common/TableSkeleton";
import { LatestStockTable } from "@/components/inventory/LatestStockTable";
import { StockSnapshotHistory } from "@/components/inventory/StockSnapshotHistory";
import { UsageHistoryTable } from "@/components/inventory/UsageHistoryTable";
import { WasteFactorTable } from "@/components/inventory/WasteFactorTable";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  useImportSnapshots,
  useImportUsage,
  useLatestStock,
  useMaterialUsage,
  useStockSnapshots,
  useWasteFactors,
} from "@/hooks/useInventory";
import { useMaterials } from "@/hooks/useMaterials";
import { useCan } from "@/hooks/usePermission";
import { useProducts } from "@/hooks/useProducts";
import { MATERIAL_USAGE_TEMPLATE, STOCK_SNAPSHOT_TEMPLATE } from "@/lib/templates";
import type { Material } from "@/types/material";

// Data input tahap 3–4 thesis (Fase 11.1/11.5): stok awal dari ERP dan pemakaian aktual (dasar
// buffer stock / faktor waste). Kedatangan bukan input lagi (20 Nov 2026): dihitung sistem dari ROP
// dan ditampilkan di halaman Kedatangan Material (/material-arrivals).
// Riwayat per material (CR v3.5 §5.2): data baru dimuat setelah material dipilih — satu
// material bisa punya puluhan snapshot/periode, jadi tidak dimuat semua sekaligus.
function MaterialHistory({
  title,
  materials,
  children,
}: {
  title: string;
  materials: Material[];
  children: (materialId: string) => ReactNode;
}) {
  const headingId = useId();
  const [materialId, setMaterialId] = useState("");
  return (
    <section aria-labelledby={headingId} className="flex flex-col gap-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <h2 id={headingId} className="text-base font-medium">
          {title}
        </h2>
        <label className="flex w-fit flex-col gap-1 text-sm">
          <span>Material</span>
          <select
            className="h-9 rounded-md border bg-transparent px-3 text-sm"
            value={materialId}
            onChange={(e) => setMaterialId(e.target.value)}
          >
            <option value="">Pilih material…</option>
            {materials.map((m) => (
              <option key={m.id} value={m.id}>
                {m.code} — {m.name}
              </option>
            ))}
          </select>
        </label>
      </div>
      {materialId && children(materialId)}
    </section>
  );
}

function SnapshotHistory({ materialId }: { materialId: string }) {
  const q = useStockSnapshots(materialId);
  return q.isPending ? <TableSkeleton /> : <StockSnapshotHistory snapshots={q.data ?? []} />;
}

function UsageHistory({ materialId }: { materialId: string }) {
  const q = useMaterialUsage(materialId);
  const { data: products } = useProducts();
  return q.isPending ? <TableSkeleton /> : <UsageHistoryTable rows={q.data ?? []} products={products ?? []} />;
}

export default function InventoryPage() {
  const { data: materials } = useMaterials();
  const latest = useLatestStock();
  const waste = useWasteFactors();
  const importSnapshots = useImportSnapshots();
  const importUsage = useImportUsage();
  const canImport = useCan("data.import_stock");

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
            {canImport && (
              <ImportButton label="Import stok ERP" pending={importSnapshots.isPending} onFile={(f) => importSnapshots.mutate(f, imported)} />
            )}
          </div>
          {canImport && <ImportTemplateCard template={STOCK_SNAPSHOT_TEMPLATE} />}
          {latest.isPending ? <TableSkeleton /> : <LatestStockTable latest={latest.data ?? []} materials={list} />}
          <MaterialHistory title="Riwayat stok ERP" materials={list}>
            {(id) => <SnapshotHistory materialId={id} />}
          </MaterialHistory>
        </TabsContent>

        <TabsContent value="usage" className="flex flex-col gap-4">
          <Alert>
            <AlertDescription>
              Kolom: <code>material_code</code>, <code>period</code>, <code>actual_usage</code>, dan{" "}
              <code>standard_usage</code> — atau <code>product_code</code> + <code>production_output</code> (standar = output × BOM).
              Buffer = max(0, Σaktual ÷ Σstandar − 1) × kebutuhan periode.
            </AlertDescription>
          </Alert>
          {canImport && (
            <div>
              <ImportButton label="Import pemakaian" pending={importUsage.isPending} onFile={(f) => importUsage.mutate(f, imported)} />
            </div>
          )}
          {canImport && <ImportTemplateCard template={MATERIAL_USAGE_TEMPLATE} />}
          {waste.isPending ? <TableSkeleton /> : <WasteFactorTable factors={waste.data ?? []} materials={list} />}
          <MaterialHistory title="Riwayat pemakaian" materials={list}>
            {(id) => <UsageHistory materialId={id} />}
          </MaterialHistory>
        </TabsContent>
      </Tabs>
    </div>
  );
}
