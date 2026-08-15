"use client";

import { Plus } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/components/common/PageHeader";
import { TableSkeleton } from "@/components/common/TableSkeleton";
import { ProductForm } from "@/components/products/ProductForm";
import { ProductsTable } from "@/components/products/ProductsTable";
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
  const [open, setOpen] = useState(false);

  const active = create.isPending || update.isPending;
  const formError = (create.error || update.error)?.message ?? null;

  const openCreate = () => {
    setEditing(null);
    setOpen(true);
  };

  const openEdit = (p: Product) => {
    setEditing(p);
    setOpen(true);
  };

  const onSubmit = (input: ProductInput) => {
    const opts = { onSuccess: () => setOpen(false) };
    if (editing) update.mutate({ id: editing.id, input }, opts);
    else create.mutate(input, opts);
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Master Data Produk"
        description="Daftar SKU produk jadi yang menjadi dasar forecast dan penurunan kebutuhan material."
        actions={
          <Button onClick={openCreate}>
            <Plus />
            Tambah produk
          </Button>
        }
      />

      {isPending && <TableSkeleton columns={5} />}
      {isError && (
        <Alert variant="destructive">
          <AlertDescription>Gagal memuat data produk.</AlertDescription>
        </Alert>
      )}
      {products && <ProductsTable products={products} onEdit={openEdit} onDelete={(p) => remove.mutate(p.id)} />}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{editing ? "Ubah produk" : "Tambah produk"}</DialogTitle>
            <DialogDescription>
              {editing
                ? "Perubahan berlaku untuk forecast berikutnya, bukan run yang sudah jalan."
                : "Kode SKU harus unik dan dipakai sebagai kunci saat mengunggah data demand."}
            </DialogDescription>
          </DialogHeader>
          {/* key memaksa form dibuat ulang saat berganti target, supaya nilai awal ikut berubah. */}
          <ProductForm
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
