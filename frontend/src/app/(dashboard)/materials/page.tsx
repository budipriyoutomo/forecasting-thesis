"use client";

import { Plus } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/components/common/PageHeader";
import { TableSkeleton } from "@/components/common/TableSkeleton";
import { MaterialForm } from "@/components/materials/MaterialForm";
import { MaterialsTable } from "@/components/materials/MaterialsTable";
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
  useCreateMaterial,
  useDeleteMaterial,
  useMaterials,
  useUpdateMaterial,
} from "@/hooks/useMaterials";
import type { Material, MaterialInput } from "@/types/material";

export default function MaterialsPage() {
  const { data: materials, isPending, isError } = useMaterials();
  const create = useCreateMaterial();
  const update = useUpdateMaterial();
  const remove = useDeleteMaterial();

  const [editing, setEditing] = useState<Material | null>(null);
  const [open, setOpen] = useState(false);

  const active = create.isPending || update.isPending;
  const formError = (create.error || update.error)?.message ?? null;

  const openCreate = () => {
    setEditing(null);
    setOpen(true);
  };

  const onSubmit = (input: MaterialInput) => {
    const opts = { onSuccess: () => setOpen(false) };
    if (editing) update.mutate({ id: editing.id, input }, opts);
    else create.mutate(input, opts);
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Master Data Material"
        description="Material dan packaging turunan produk. Lead time dan MOQ di sini dipakai saat menghitung reorder."
        actions={
          <Button onClick={openCreate}>
            <Plus />
            Tambah material
          </Button>
        }
      />

      {isPending && <TableSkeleton columns={6} />}
      {isError && (
        <Alert variant="destructive">
          <AlertDescription>Gagal memuat data material.</AlertDescription>
        </Alert>
      )}
      {materials && (
        <MaterialsTable
          materials={materials}
          onEdit={(m) => {
            setEditing(m);
            setOpen(true);
          }}
          onDelete={(m) => remove.mutate(m.id)}
        />
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{editing ? "Ubah material" : "Tambah material"}</DialogTitle>
            <DialogDescription>
              Lead time dan MOQ langsung memengaruhi safety stock serta EOQ pada run berikutnya.
            </DialogDescription>
          </DialogHeader>
          <MaterialForm
            key={editing?.id ?? "baru"}
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
