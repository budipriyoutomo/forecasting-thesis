"use client";

import { Plus } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/components/common/PageHeader";
import { TableSkeleton } from "@/components/common/TableSkeleton";
import { CostTemplateForm } from "@/components/cost-templates/CostTemplateForm";
import { CostTemplateSummaryPanel } from "@/components/cost-templates/CostTemplateSummaryPanel";
import { CostTemplatesTable } from "@/components/cost-templates/CostTemplatesTable";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import {
  useActivateCostTemplate,
  useCostTemplateSummary,
  useCostTemplates,
  useCreateCostTemplate,
  useDeactivateCostTemplate,
  useDeleteCostTemplate,
  useUpdateCostTemplate,
} from "@/hooks/useCostTemplates";
import { useMaterials } from "@/hooks/useMaterials";
import { useCan } from "@/hooks/usePermission";
import type { CostTemplate, CostTemplateInput } from "@/types/costTemplate";

export default function CostTemplatesPage() {
  const { data: templates, isPending, isError } = useCostTemplates();
  const { data: materials } = useMaterials();
  const create = useCreateCostTemplate();
  const update = useUpdateCostTemplate();
  const activate = useActivateCostTemplate();
  const deactivate = useDeactivateCostTemplate();
  const remove = useDeleteCostTemplate();
  const canWrite = useCan("master.write");

  const [editing, setEditing] = useState<CostTemplate | null>(null);
  const [open, setOpen] = useState(false);
  // "Lihat ringkasan" membuka panel samping (21 Nov 2026). Sebelumnya panel inline di bawah tabel
  // sudah menampilkan template aktif sejak awal, jadi klik pada template yang sama tampak tidak
  // berbuat apa-apa, dan error ringkasan tidak pernah ditampilkan.
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected = templates?.find((t) => t.id === selectedId) ?? null;
  const summary = useCostTemplateSummary(selected?.id ?? null);
  const active = templates?.find((t) => t.is_active);

  const formError = (create.error || update.error)?.message ?? null;

  const onSubmit = (input: CostTemplateInput) => {
    const opts = { onSuccess: () => setOpen(false) };
    if (editing) update.mutate({ id: editing.id, input }, opts);
    else create.mutate(input, opts);
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Template Biaya"
        description="Biaya pesan (S) dan biaya simpan (H) untuk EOQ & total biaya persediaan, beserta rincian overhead dan depresiasi aset penyimpanan sebagai dasar menentukan H."
        actions={
          canWrite && (
            <Button
              onClick={() => {
                setEditing(null);
                setOpen(true);
              }}
            >
              <Plus />
              Tambah template
            </Button>
          )
        }
      />

      {templates && !active && (
        <Alert>
          <AlertDescription>
            Belum ada template aktif — perhitungan EOQ & total biaya memakai biaya default sistem.
          </AlertDescription>
        </Alert>
      )}

      {isPending && <TableSkeleton columns={5} />}
      {isError && (
        <Alert variant="destructive">
          <AlertDescription>Gagal memuat template biaya.</AlertDescription>
        </Alert>
      )}
      {(activate.error || deactivate.error || remove.error) && (
        <Alert variant="destructive">
          <AlertDescription>{(activate.error || deactivate.error || remove.error)?.message}</AlertDescription>
        </Alert>
      )}
      {templates && (
        <CostTemplatesTable
          templates={templates}
          onSelect={(t) => setSelectedId(t.id)}
          onEdit={
            canWrite
              ? (t) => {
                  setEditing(t);
                  setOpen(true);
                }
              : undefined
          }
          onActivate={canWrite ? (t) => activate.mutate(t.id) : undefined}
          onDeactivate={canWrite ? (t) => deactivate.mutate(t.id) : undefined}
          onDelete={canWrite ? (t) => remove.mutate(t.id) : undefined}
        />
      )}

      <Sheet open={selected !== null} onOpenChange={(o) => !o && setSelectedId(null)}>
        <SheetContent className="w-full overflow-y-auto sm:max-w-3xl">
          <SheetHeader>
            <SheetTitle>Ringkasan — {selected?.name}</SheetTitle>
            <SheetDescription>
              Komponen biaya per bulan, saran biaya simpan (H) & i (%), dan harga pembelian material.
            </SheetDescription>
          </SheetHeader>
          <div className="px-4 pb-6">
            {summary.isPending && <Skeleton className="h-40 w-full" />}
            {summary.isError && (
              <Alert variant="destructive">
                <AlertDescription>Gagal memuat ringkasan: {summary.error.message}</AlertDescription>
              </Alert>
            )}
            {selected && summary.data && (
              <CostTemplateSummaryPanel template={selected} summary={summary.data} materials={materials ?? []} />
            )}
          </div>
        </SheetContent>
      </Sheet>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>{editing ? "Ubah template biaya" : "Tambah template biaya"}</DialogTitle>
            <DialogDescription>
              Template baru tidak langsung aktif — aktifkan dari tabel agar dipakai perhitungan
              EOQ.
            </DialogDescription>
          </DialogHeader>
          <CostTemplateForm
            key={editing?.id ?? "baru"}
            initial={editing ?? undefined}
            onSubmit={onSubmit}
            submitting={create.isPending || update.isPending}
            error={formError}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
}
