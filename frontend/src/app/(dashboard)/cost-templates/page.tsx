"use client";

import { Plus } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/components/common/PageHeader";
import { TableSkeleton } from "@/components/common/TableSkeleton";
import { CostTemplateForm } from "@/components/cost-templates/CostTemplateForm";
import { CostTemplateSummaryPanel } from "@/components/cost-templates/CostTemplateSummaryPanel";
import { CostTemplatesTable } from "@/components/cost-templates/CostTemplatesTable";
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
  useActivateCostTemplate,
  useCostTemplateSummary,
  useCostTemplates,
  useCreateCostTemplate,
  useDeleteCostTemplate,
  useUpdateCostTemplate,
} from "@/hooks/useCostTemplates";
import { useMaterials } from "@/hooks/useMaterials";
import type { CostTemplate, CostTemplateInput } from "@/types/costTemplate";

export default function CostTemplatesPage() {
  const { data: templates, isPending, isError } = useCostTemplates();
  const { data: materials } = useMaterials();
  const create = useCreateCostTemplate();
  const update = useUpdateCostTemplate();
  const activate = useActivateCostTemplate();
  const remove = useDeleteCostTemplate();

  const [editing, setEditing] = useState<CostTemplate | null>(null);
  const [open, setOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Ringkasan default: template aktif, atau yang pertama bila belum ada yang aktif.
  const selected =
    templates?.find((t) => t.id === selectedId) ??
    templates?.find((t) => t.is_active) ??
    templates?.[0] ??
    null;
  const { data: summary } = useCostTemplateSummary(selected?.id ?? null);
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
          <Button
            onClick={() => {
              setEditing(null);
              setOpen(true);
            }}
          >
            <Plus />
            Tambah template
          </Button>
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
      {(activate.error || remove.error) && (
        <Alert variant="destructive">
          <AlertDescription>{(activate.error || remove.error)?.message}</AlertDescription>
        </Alert>
      )}
      {templates && (
        <CostTemplatesTable
          templates={templates}
          onSelect={(t) => setSelectedId(t.id)}
          onEdit={(t) => {
            setEditing(t);
            setOpen(true);
          }}
          onActivate={(t) => activate.mutate(t.id)}
          onDelete={(t) => remove.mutate(t.id)}
        />
      )}

      {selected && summary && (
        <CostTemplateSummaryPanel template={selected} summary={summary} materials={materials ?? []} />
      )}

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
