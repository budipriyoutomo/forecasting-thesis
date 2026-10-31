"use client";

import { useState } from "react";
import { toast } from "sonner";

import { ImportButton } from "@/components/common/ImportButton";
import { PageHeader } from "@/components/common/PageHeader";
import { TableSkeleton } from "@/components/common/TableSkeleton";
import { LatestStockTable } from "@/components/inventory/LatestStockTable";
import { ReceiptForm } from "@/components/inventory/ReceiptForm";
import { ReceiptsTable } from "@/components/inventory/ReceiptsTable";
import { WasteFactorTable } from "@/components/inventory/WasteFactorTable";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  useCreateReceipt,
  useDeleteReceipt,
  useImportReceipts,
  useImportSnapshots,
  useImportUsage,
  useLatestStock,
  useReceipts,
  useWasteFactors,
} from "@/hooks/useInventory";
import { useMaterials } from "@/hooks/useMaterials";

// Data input tahap 3–4 thesis (Fase 11.1/11.5): stok awal dari ERP, estimasi kedatangan,
// dan pemakaian aktual (dasar buffer stock / faktor waste).
export default function InventoryPage() {
  const { data: materials } = useMaterials();
  const latest = useLatestStock();
  const receipts = useReceipts();
  const waste = useWasteFactors();
  const importSnapshots = useImportSnapshots();
  const importReceipts = useImportReceipts();
  const importUsage = useImportUsage();
  const createReceipt = useCreateReceipt();
  const deleteReceipt = useDeleteReceipt();
  const [formKey, setFormKey] = useState(0);

  const imported = { onSuccess: (r: { imported: number }) => toast.success(`${r.imported} baris diimpor`), onError: (e: Error) => toast.error(e.message) };
  const list = materials ?? [];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Persediaan Material"
        description="Stok awal dari ERP, estimasi kedatangan, dan pemakaian aktual material — input proyeksi stok, utilisasi gudang, dan buffer stock."
      />
      <Tabs defaultValue="stock">
        <TabsList>
          <TabsTrigger value="stock">Stok ERP</TabsTrigger>
          <TabsTrigger value="receipts">Kedatangan</TabsTrigger>
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

        <TabsContent value="receipts" className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
          <div className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm text-muted-foreground">
                Kolom import: <code>material_code</code>, <code>expected_date</code>, <code>qty</code> [, <code>note</code>].
              </p>
              <ImportButton label="Import kedatangan" pending={importReceipts.isPending} onFile={(f) => importReceipts.mutate(f, imported)} />
            </div>
            {receipts.isPending ? (
              <TableSkeleton />
            ) : (
              <ReceiptsTable
                receipts={receipts.data ?? []}
                materials={list}
                onDelete={(r) => deleteReceipt.mutate(r.id, { onError: (e) => toast.error(e.message) })}
              />
            )}
          </div>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Input manual</CardTitle>
              <CardDescription>Rencana kedatangan material dari PO/supplier.</CardDescription>
            </CardHeader>
            <CardContent>
              <ReceiptForm
                key={formKey}
                materials={list}
                submitting={createReceipt.isPending}
                error={createReceipt.error?.message ?? null}
                onSubmit={(input) => createReceipt.mutate(input, { onSuccess: () => setFormKey((k) => k + 1) })}
              />
            </CardContent>
          </Card>
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
