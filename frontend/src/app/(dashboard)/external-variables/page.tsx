"use client";

import { Plus } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { ImportButton } from "@/components/common/ImportButton";
import { PageHeader } from "@/components/common/PageHeader";
import { TableSkeleton } from "@/components/common/TableSkeleton";
import { ExternalVariableForm } from "@/components/external-variables/ExternalVariableForm";
import { ExternalVariablesTable } from "@/components/external-variables/ExternalVariablesTable";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import {
  useDeleteExternalVariable,
  useExternalVariables,
  useImportExternalValues,
  useSaveExternalVariable,
} from "@/hooks/useExternalVariables";
import type { ExternalVariable } from "@/types/externalVariable";

export default function ExternalVariablesPage() {
  const { data, isPending, isError } = useExternalVariables();
  const save = useSaveExternalVariable();
  const remove = useDeleteExternalVariable();
  const importValues = useImportExternalValues();
  const [editing, setEditing] = useState<ExternalVariable | null>(null);
  const [open, setOpen] = useState(false);

  const onError = (e: Error) => toast.error(e.message);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Variabel Eksternal"
        description="Musim, cuaca & temperatur, harga, promosi & event — dipakai Random Forest & XGBoost sebagai fitur tambahan. Hanya variabel aktif yang nilainya lengkap untuk histori dan seluruh periode horizon yang ikut dipakai."
        actions={
          <div className="flex flex-wrap gap-2">
            <ImportButton
              label="Import nilai"
              pending={importValues.isPending}
              onFile={(file) =>
                importValues.mutate(file, {
                  onSuccess: (r) => toast.success(`${r.imported} nilai diimpor`),
                  onError,
                })
              }
            />
            <Button
              onClick={() => {
                setEditing(null);
                setOpen(true);
              }}
            >
              <Plus />
              Tambah variabel
            </Button>
          </div>
        }
      />

      <Alert>
        <AlertDescription>
          Format import: kolom <code>variable_code</code>, <code>period</code>, <code>value</code>, dan{" "}
          <code>product_code</code> (wajib untuk variabel per produk, kosong untuk global). Variabel flag bernilai 0/1.
          Nilai dengan periode sama akan ditimpa.
        </AlertDescription>
      </Alert>

      {isError && (
        <Alert variant="destructive">
          <AlertDescription>Gagal memuat variabel eksternal.</AlertDescription>
        </Alert>
      )}

      {isPending ? (
        <TableSkeleton />
      ) : (
        <ExternalVariablesTable
          variables={data ?? []}
          onToggle={(v, next) => save.mutate({ id: v.id, input: { is_active: next } }, { onError })}
          onEdit={(v) => {
            setEditing(v);
            setOpen(true);
          }}
          onClearValues={(v) => remove.mutate({ id: v.id, valuesOnly: true }, { onError })}
          onDelete={(v) => remove.mutate({ id: v.id }, { onError })}
        />
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editing ? `Ubah ${editing.code}` : "Tambah variabel eksternal"}</DialogTitle>
            <DialogDescription>Kode dipakai sebagai nama fitur model dan tidak bisa diubah setelah dibuat.</DialogDescription>
          </DialogHeader>
          <ExternalVariableForm
            key={editing?.id ?? "new"}
            initial={editing ?? undefined}
            submitting={save.isPending}
            error={save.error?.message ?? null}
            onSubmit={(input) => save.mutate({ id: editing?.id, input }, { onSuccess: () => setOpen(false) })}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
}
