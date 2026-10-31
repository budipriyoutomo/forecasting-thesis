"use client";

import { Plus } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/components/common/PageHeader";
import { TableSkeleton } from "@/components/common/TableSkeleton";
import { WarehouseConfigForm } from "@/components/warehouse/WarehouseConfigForm";
import { WarehouseConfigTable } from "@/components/warehouse/WarehouseConfigTable";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  useCreateWarehouseConfig,
  useDeleteWarehouseConfig,
  useUpdateWarehouseConfig,
  useWarehouseConfigs,
} from "@/hooks/useWarehouse";
import { useMaterials } from "@/hooks/useMaterials";
import { useProducts } from "@/hooks/useProducts";
import type { WarehouseConfig, WarehouseConfigInput, WarehouseTarget } from "@/types/warehouse";

export default function WarehousePage() {
  const { data: configs, isPending, isError } = useWarehouseConfigs();
  const { data: products } = useProducts();
  const { data: materials } = useMaterials();
  // Fase 11.6 (Keputusan #1): gudang produk jadi & gudang material dikelola terpisah.
  const [target, setTarget] = useState<WarehouseTarget>("material");
  const shown = (configs ?? []).filter((c) => (c.item_type ?? "product") === target);
  const create = useCreateWarehouseConfig();
  const update = useUpdateWarehouseConfig();
  const remove = useDeleteWarehouseConfig();

  const [editing, setEditing] = useState<WarehouseConfig | null>(null);
  const [open, setOpen] = useState(false);

  const active = create.isPending || update.isPending;
  const formError = (create.error || update.error)?.message ?? null;

  const onSubmit = (input: WarehouseConfigInput) => {
    const opts = { onSuccess: () => setOpen(false) };
    if (editing) {
      const { product_id: _productId, material_id: _materialId, item_type: _itemType, ...capacity } = input;
      update.mutate({ id: editing.id, input: capacity }, opts);
    } else create.mutate(input, opts);
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Kapasitas Gudang"
        description="Kapasitas gudang material (pallet → CTN → pcs, dipakai proyeksi stok & utilisasi thesis) dan gudang produk jadi (pallet/dus, validasi forecast produk)."
        actions={
          <Button
            onClick={() => {
              setEditing(null);
              setOpen(true);
            }}
          >
            <Plus />
            Tambah kapasitas
          </Button>
        }
      />

      <Tabs value={target} onValueChange={(v) => setTarget(v as WarehouseTarget)}>
        <TabsList>
          <TabsTrigger value="material">Material</TabsTrigger>
          <TabsTrigger value="product">Produk jadi</TabsTrigger>
        </TabsList>
      </Tabs>

      {isPending && <TableSkeleton columns={5} />}
      {isError && (
        <Alert variant="destructive">
          <AlertDescription>Gagal memuat konfigurasi gudang.</AlertDescription>
        </Alert>
      )}
      {configs && (
        <WarehouseConfigTable
          configs={shown}
          products={products ?? []}
          materials={materials ?? []}
          targetType={target}
          onEdit={(c) => {
            setEditing(c);
            setOpen(true);
          }}
          onDelete={(c) => remove.mutate(c.id)}
        />
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{editing ? "Ubah kapasitas" : "Tambah kapasitas"}</DialogTitle>
            <DialogDescription>
              {target === "material"
                ? "Isi kapasitas dalam pallet, CTN, atau kombinasi. Bila unit material bukan CTN/dus, isi juga pcs per CTN agar bisa dibandingkan dengan proyeksi stok."
                : "Isi kapasitas dalam pallet, dus, atau kombinasi. Bila unit produk bukan dus/karton/box, isi juga jumlah pcs per dus agar bisa dibandingkan dengan forecast."}
            </DialogDescription>
          </DialogHeader>
          <WarehouseConfigForm
            key={`${target}:${editing?.id ?? "baru"}`}
            products={products ?? []}
            materials={materials ?? []}
            targetType={target}
            initial={editing ?? undefined}
            onSubmit={onSubmit}
            submitting={active}
            error={formError}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
}
