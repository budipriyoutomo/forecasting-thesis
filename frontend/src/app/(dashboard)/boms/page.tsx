"use client";

import { Plus } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/components/common/PageHeader";
import { TableSkeleton } from "@/components/common/TableSkeleton";
import { BomComponentForm } from "@/components/boms/BomComponentForm";
import { BomCostSummary } from "@/components/boms/BomCostSummary";
import { BomForm } from "@/components/boms/BomForm";
import { BomMultiForm } from "@/components/boms/BomMultiForm";
import { BomTree } from "@/components/boms/BomTree";
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
import {
  useBoms,
  useCreateBomsBulk,
  useDeleteBom,
  useMaterialComponents,
  useUpdateBom,
} from "@/hooks/useBoms";
import { useMaterials } from "@/hooks/useMaterials";
import { useCan } from "@/hooks/usePermission";
import { useBomComponent, useBomTree } from "@/hooks/usePlanning";
import { useProducts } from "@/hooks/useProducts";
import type { Bom, BomBulkInput, BomInput } from "@/types/bom";

// Radix Select tidak menerima value "" untuk sebuah item, jadi "semua produk"
// diwakili sentinel dan diterjemahkan ke null saat query.
const SEMUA = "__semua__";

export default function BomsPage() {
  const [filterProduct, setFilterProduct] = useState<string>(SEMUA);
  const productFilter = filterProduct === SEMUA ? null : filterProduct;
  const { data: boms, isPending, isError } = useBoms(productFilter);
  const { data: products } = useProducts();
  const { data: materials } = useMaterials();
  const create = useCreateBomsBulk();
  // 19 Nov 2026: komponen level 2+ untuk kolom Level di tabel BOM
  const { data: components } = useMaterialComponents();
  const update = useUpdateBom();
  const remove = useDeleteBom();
  const canWrite = useCan("master.write");
  // Fase 11.3: tree multi-level FG → material → komponen untuk produk yang difilter.
  const tree = useBomTree(productFilter);
  const component = useBomComponent();

  const [editing, setEditing] = useState<Bom | null>(null);
  const [open, setOpen] = useState(false);

  const active = create.isPending || update.isPending;
  const formError = (create.error || update.error)?.message ?? null;

  const opts = { onSuccess: () => setOpen(false) };
  const onUpdate = (input: BomInput) => editing && update.mutate({ id: editing.id, input }, opts);
  const onCreate = (input: BomBulkInput) => create.mutate(input, opts);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Bill of Materials"
        description="Takaran material per unit produk. Inilah yang menurunkan hasil forecast produk menjadi kebutuhan material."
        actions={
          canWrite && (
            <Button
              onClick={() => {
                setEditing(null);
                setOpen(true);
              }}
            >
              <Plus />
              Tambah BOM
            </Button>
          )
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

      {isPending && <TableSkeleton columns={5} />}
      {isError && (
        <Alert variant="destructive">
          <AlertDescription>Gagal memuat data BOM.</AlertDescription>
        </Alert>
      )}
      {boms && <BomCostSummary boms={boms} products={products ?? []} />}
      {tree.data && (
        <section className="flex flex-col gap-3">
          <div>
            <h2 className="text-base font-medium">Struktur BOM multi-level</h2>
            <p className="text-sm text-muted-foreground">
              Level 1 = material yang dibeli (masuk EOQ & kapasitas). Level 2 (mis. Preform untuk Bottle) hanya
              informasi — Bottle dibeli jadi.
            </p>
          </div>
          <BomTree tree={tree.data} onRemove={canWrite ? (id) => component.mutate({ removeId: id }) : undefined} />
          {canWrite && (
            <BomComponentForm
              parents={tree.data.children.map((c) => ({ id: c.material_id as string, code: c.code ?? "" }))}
              materials={materials ?? []}
              submitting={component.isPending}
              error={component.error?.message ?? null}
              onSubmit={(input) => component.mutate(input)}
            />
          )}
        </section>
      )}
      {boms && (
        <BomsTable
          boms={boms}
          components={components ?? []}
          products={products ?? []}
          materials={materials ?? []}
          onEdit={
            canWrite
              ? (b) => {
                  setEditing(b);
                  setOpen(true);
                }
              : undefined
          }
          onDelete={canWrite ? (b) => remove.mutate(b.id) : undefined}
        />
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{editing ? "Ubah baris BOM" : "Tambah BOM"}</DialogTitle>
            <DialogDescription>
              Qty per unit adalah jumlah material (level 1) yang dipakai untuk satu unit produk jadi.
              {!editing && " Tambahkan beberapa material sekaligus untuk produk yang sama."}
            </DialogDescription>
          </DialogHeader>
          {editing ? (
            <BomForm
              key={editing.id}
              products={products ?? []}
              materials={materials ?? []}
              initial={editing}
              onSubmit={onUpdate}
              submitting={active}
              error={formError}
            />
          ) : (
            <BomMultiForm
              key={open ? "baru-open" : "baru"}
              products={products ?? []}
              materials={materials ?? []}
              defaultProductId={productFilter ?? undefined}
              onSubmit={onCreate}
              submitting={active}
              error={formError}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
