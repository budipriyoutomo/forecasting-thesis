"use client";

import { Download, Plus } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";

import { ImportButton } from "@/components/common/ImportButton";
import { PageHeader } from "@/components/common/PageHeader";
import { TableSkeleton } from "@/components/common/TableSkeleton";
import { ExternalVariableForm } from "@/components/external-variables/ExternalVariableForm";
import { ExternalVariablesTable } from "@/components/external-variables/ExternalVariablesTable";
import { ImportValidationResult } from "@/components/external-variables/ImportValidationResult";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import {
  useDeleteExternalVariable,
  useDownloadExternalTemplate,
  useExternalVariableCoverage,
  useExternalVariables,
  useImportExternalValues,
  useSaveExternalVariable,
  useValidateExternalValues,
} from "@/hooks/useExternalVariables";
import { importSummary } from "@/lib/externalVariable";
import type { ExternalVariable } from "@/types/externalVariable";

export default function ExternalVariablesPage() {
  const { data, isPending, isError } = useExternalVariables();
  const coverage = useExternalVariableCoverage();
  const coverageById = useMemo(
    () => Object.fromEntries((coverage.data ?? []).map((c) => [c.variable_id, c])),
    [coverage.data],
  );
  const save = useSaveExternalVariable();
  const remove = useDeleteExternalVariable();
  const importValues = useImportExternalValues();
  const validateValues = useValidateExternalValues();
  const template = useDownloadExternalTemplate();
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
            <Button variant="outline" disabled={template.isPending} onClick={() => template.mutate(undefined, { onError })}>
              <Download />
              Unduh template
            </Button>
            <ImportButton
              label="Validasi file"
              pendingLabel="Memvalidasi…"
              pending={validateValues.isPending}
              onFile={(file) => validateValues.mutate(file, { onError })}
            />
            <ImportButton
              label="Import nilai"
              pending={importValues.isPending}
              onFile={(file) =>
                importValues.mutate(file, {
                  onSuccess: (r) => {
                    validateValues.reset();
                    toast.success(importSummary(r));
                  },
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
          Dua format import (terdeteksi otomatis). <strong>Lebar</strong> (sama dengan template): kolom{" "}
          <code>period</code>, satu kolom per kode variabel, dan <code>product_code</code> untuk variabel per produk.{" "}
          <strong>Panjang</strong>: kolom <code>variable_code</code>, <code>period</code>, <code>value</code>, dan{" "}
          <code>product_code</code> (wajib untuk variabel per produk, kosong untuk global). Variabel flag bernilai 0/1.
          Koma desimal, <code>Rp</code>, dan <code>%</code> diterima; sel kosong, <code>-</code>, atau <code>NA</code>{" "}
          dilewati. Pakai <em>Validasi file</em> untuk melihat semua error sebelum import.
          Periode digeser ke awal bulan (mis. 2024-01-24 → 2024-01-01); nilai dengan bulan sama akan ditimpa.
          Kolom <em>Kelengkapan</em> = periode terisi dibanding periode demand + 12 bulan ke depan. Variabel
          yang belum lengkap tidak dipakai model ML.
        </AlertDescription>
      </Alert>

      {validateValues.data && <ImportValidationResult result={validateValues.data} />}

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
          coverage={coverageById}
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
