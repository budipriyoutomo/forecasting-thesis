"use client";

import { useState } from "react";

import { MaterialForm } from "@/components/materials/MaterialForm";
import { MaterialsTable } from "@/components/materials/MaterialsTable";
import { Button } from "@/components/ui/button";
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
  const [showForm, setShowForm] = useState(false);

  const active = create.isPending || update.isPending;
  const formError = (create.error || update.error)?.message ?? null;

  const onSubmit = (input: MaterialInput) => {
    const opts = {
      onSuccess: () => {
        setShowForm(false);
        setEditing(null);
      },
    };
    if (editing) update.mutate({ id: editing.id, input }, opts);
    else create.mutate(input, opts);
  };

  return (
    <main className="container flex min-h-screen flex-col gap-6 py-16">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Master Data Material</h1>
        <Button
          onClick={() => {
            setEditing(null);
            setShowForm((v) => !v);
          }}
        >
          {showForm ? "Tutup" : "Tambah material"}
        </Button>
      </div>

      {showForm && (
        <div className="max-w-md rounded-lg border p-4">
          <MaterialForm
            initial={editing ?? undefined}
            onSubmit={onSubmit}
            submitting={active}
            error={formError}
          />
        </div>
      )}

      {isPending && <p className="text-sm text-muted-foreground">Memuat material…</p>}
      {isError && <p className="text-sm text-destructive">Gagal memuat data material.</p>}
      {materials && (
        <MaterialsTable
          materials={materials}
          onEdit={(m) => {
            setEditing(m);
            setShowForm(true);
          }}
          onDelete={(m) => remove.mutate(m.id)}
        />
      )}
    </main>
  );
}
