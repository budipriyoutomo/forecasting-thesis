"use client";

import { Plus } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/components/common/PageHeader";
import { TableSkeleton } from "@/components/common/TableSkeleton";
import { BomForm } from "@/components/boms/BomForm";
import { BomsTable } from "@/components/boms/BomsTable";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useBoms, useCreateBom, useDeleteBom, useUpdateBom } from "@/hooks/useBoms";
import { useMaterials } from "@/hooks/useMaterials";
import { useProducts } from "@/hooks/useProducts";
import type { Bom, BomInput } from "@/types/bom";

// Radix Select tidak menerima value "" untuk sebuah item, jadi "semua produk"
// diwakili sentinel dan diterjemahkan ke null saat query.
const SEMUA = "__semua__";

export default function BomsPage() {
  const [filterProduct, setFilterProduct] = useState<string>(SEMUA);
  const productFilter = filterProduct === SEMUA ? null : filterProduct;
  const { data: boms, isPending, isError } = useBoms(productFilter);
  const { data: products } = useProducts();
  const { data: materials } = useMaterials();
  const create = useCreateBom();
  const update = useUpdateBom();
  const remove = useDeleteBom();

  const [editing, setEditing] = useState<Bom | null>(null);
  const [open, setOpen] = useState(false);

  const active = create.isPending || update.isPending;
  const formError = (create.error || update.error)?.message ?? null;

  const onSubmit = (input: BomInput) => {
    const opts = { onSuccess: () => setOpen(false) };
    if (editing) update.mutate({ id: editing.id, input }, opts);
    else create.mutate(input, opts);
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Bill of Materials"
        description="Takaran material per unit produk. Inilah yang menurunkan hasil forecast produk menjadi kebutuhan material."
        actions={
          <Button
            onClick={() => {
              setEditing(null);
              setOpen(true);
            }}
          >
            <Plus />
            Tambah BOM
          </Button>
        }
      />

      <div className="flex items-center gap-2">
        <Label htmlFor="filter-produk" className="text-muted-foreground">
          Filter produk
        </Label>
        <Select value={filterProduct} onValueChange={setFilterProduct}>
          <SelectTrigger id="filter-produk" className="w-[280px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={SEMUA}>Semua produk</SelectItem>
            {(products ?? []).map((p) => (
              <SelectItem key={p.id} value={p.id}>
                {p.code} — {p.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {isPending && <TableSkeleton columns={4} />}
      {isError && (
        <Alert variant="destructive">
          <AlertDescription>Gagal memuat data BOM.</AlertDescription>
        </Alert>
      )}
      {boms && (
        <BomsTable
          boms={boms}
          products={products ?? []}
          materials={materials ?? []}
          onEdit={(b) => {
            setEditing(b);
            setOpen(true);
          }}
          onDelete={(b) => remove.mutate(b.id)}
        />
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{editing ? "Ubah baris BOM" : "Tambah baris BOM"}</DialogTitle>
            <DialogDescription>
              Qty per unit adalah jumlah material yang dipakai untuk satu unit produk jadi.
            </DialogDescription>
          </DialogHeader>
          <BomForm
            key={editing?.id ?? "baru"}
            products={products ?? []}
            materials={materials ?? []}
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
