"use client";

import { Plus } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/components/common/PageHeader";
import { TableSkeleton } from "@/components/common/TableSkeleton";
import { WarehouseConfigForm } from "@/components/warehouse/WarehouseConfigForm";
import { WarehouseConfigTable } from "@/components/warehouse/WarehouseConfigTable";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
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
import { useProducts } from "@/hooks/useProducts";
import type { WarehouseConfig, WarehouseConfigInput } from "@/types/warehouse";

export default function WarehousePage() {
  const { data: configs, isPending, isError } = useWarehouseConfigs();
  const { data: products } = useProducts();
  const create = useCreateWarehouseConfig();
  const update = useUpdateWarehouseConfig();
  const remove = useDeleteWarehouseConfig();

  const [editing, setEditing] = useState<WarehouseConfig | null>(null);
  const [open, setOpen] = useState(false);

  const active = create.isPending || update.isPending;
  const formError = (create.error || update.error)?.message ?? null;

  const onSubmit = (input: WarehouseConfigInput) => {
    const opts = { onSuccess: () => setOpen(false) };
    if (editing)
      update.mutate({ id: editing.id, capacity_qty: input.capacity_qty, uom: input.uom }, opts);
    else create.mutate(input, opts);
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Kapasitas Gudang"
        description="Kapasitas per produk, angka bebas — isi langsung sesuai kondisi gudang. Dipakai untuk memvalidasi apakah forecast produk muat."
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

      {isPending && <TableSkeleton columns={3} />}
      {isError && (
        <Alert variant="destructive">
          <AlertDescription>Gagal memuat konfigurasi gudang.</AlertDescription>
        </Alert>
      )}
      {configs && (
        <WarehouseConfigTable
          configs={configs}
          products={products ?? []}
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
              Kapasitas adalah angka bebas (unit produk) — isikan langsung sesuai kondisi
              gudang, tidak dihitung dari luas gudang atau dimensi palet. UOM juga isian
              bebas, tanpa master UOM.
            </DialogDescription>
          </DialogHeader>
          <WarehouseConfigForm
            key={editing?.id ?? "baru"}
            products={products ?? []}
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
