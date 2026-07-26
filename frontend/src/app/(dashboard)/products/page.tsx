"use client";

import { useState } from "react";

import { ProductForm } from "@/components/products/ProductForm";
import { ProductsTable } from "@/components/products/ProductsTable";
import { Button } from "@/components/ui/button";
import {
  useCreateProduct,
  useDeleteProduct,
  useProducts,
  useUpdateProduct,
} from "@/hooks/useProducts";
import type { Product, ProductInput } from "@/types/product";

export default function ProductsPage() {
  const { data: products, isPending, isError } = useProducts();
  const create = useCreateProduct();
  const update = useUpdateProduct();
  const remove = useDeleteProduct();

  const [editing, setEditing] = useState<Product | null>(null);
  const [showForm, setShowForm] = useState(false);

  const active = create.isPending || update.isPending;
  const formError = (create.error || update.error)?.message ?? null;

  const onSubmit = (input: ProductInput) => {
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
        <h1 className="text-2xl font-semibold">Master Data Produk</h1>
        <Button
          onClick={() => {
            setEditing(null);
            setShowForm((v) => !v);
          }}
        >
          {showForm ? "Tutup" : "Tambah produk"}
        </Button>
      </div>

      {showForm && (
        <div className="max-w-md rounded-lg border p-4">
          <ProductForm
            initial={editing ?? undefined}
            onSubmit={onSubmit}
            submitting={active}
            error={formError}
          />
        </div>
      )}

      {isPending && <p className="text-sm text-muted-foreground">Memuat produk…</p>}
      {isError && <p className="text-sm text-destructive">Gagal memuat data produk.</p>}
      {products && (
        <ProductsTable
          products={products}
          onEdit={(p) => {
            setEditing(p);
            setShowForm(true);
          }}
          onDelete={(p) => remove.mutate(p.id)}
        />
      )}
    </main>
  );
}
