"use client";

import { useState } from "react";

import { BomForm } from "@/components/boms/BomForm";
import { BomsTable } from "@/components/boms/BomsTable";
import { Button } from "@/components/ui/button";
import { useBoms, useCreateBom, useDeleteBom, useUpdateBom } from "@/hooks/useBoms";
import { useMaterials } from "@/hooks/useMaterials";
import { useProducts } from "@/hooks/useProducts";
import type { Bom, BomInput } from "@/types/bom";

export default function BomsPage() {
  const [filterProduct, setFilterProduct] = useState<string>("");
  const { data: boms, isPending, isError } = useBoms(filterProduct || null);
  const { data: products } = useProducts();
  const { data: materials } = useMaterials();
  const create = useCreateBom();
  const update = useUpdateBom();
  const remove = useDeleteBom();

  const [editing, setEditing] = useState<Bom | null>(null);
  const [showForm, setShowForm] = useState(false);

  const active = create.isPending || update.isPending;
  const formError = (create.error || update.error)?.message ?? null;

  const onSubmit = (input: BomInput) => {
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
        <h1 className="text-2xl font-semibold">Bill of Materials</h1>
        <Button
          onClick={() => {
            setEditing(null);
            setShowForm((v) => !v);
          }}
        >
          {showForm ? "Tutup" : "Tambah BOM"}
        </Button>
      </div>

      <div className="flex items-center gap-2">
        <label htmlFor="filter" className="text-sm text-muted-foreground">
          Filter produk:
        </label>
        <select
          id="filter"
          className="h-9 rounded-md border border-input bg-background px-2 text-sm"
          value={filterProduct}
          onChange={(e) => setFilterProduct(e.target.value)}
        >
          <option value="">Semua produk</option>
          {(products ?? []).map((p) => (
            <option key={p.id} value={p.id}>
              {p.code} — {p.name}
            </option>
          ))}
        </select>
      </div>

      {showForm && (
        <div className="max-w-md rounded-lg border p-4">
          <BomForm
            products={products ?? []}
            materials={materials ?? []}
            initial={editing ?? undefined}
            onSubmit={onSubmit}
            submitting={active}
            error={formError}
          />
        </div>
      )}

      {isPending && <p className="text-sm text-muted-foreground">Memuat BOM…</p>}
      {isError && <p className="text-sm text-destructive">Gagal memuat data BOM.</p>}
      {boms && (
        <BomsTable
          boms={boms}
          products={products ?? []}
          materials={materials ?? []}
          onEdit={(b) => {
            setEditing(b);
            setShowForm(true);
          }}
          onDelete={(b) => remove.mutate(b.id)}
        />
      )}
    </main>
  );
}
