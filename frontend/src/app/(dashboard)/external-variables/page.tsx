"use client";

import { Download, Plus } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";

import { ImportButton } from "@/components/common/ImportButton";
import { PageHeader } from "@/components/common/PageHeader";
import { TableSkeleton } from "@/components/common/TableSkeleton";
import { ExternalVariableForm } from "@/components/external-variables/ExternalVariableForm";
import { ExternalVariableValuesEditor } from "@/components/external-variables/ExternalVariableValuesEditor";
import { ExternalVariableValuesTable } from "@/components/external-variables/ExternalVariableValuesTable";
import { ExternalVariablesTable } from "@/components/external-variables/ExternalVariablesTable";
import { ImportValidationResult } from "@/components/external-variables/ImportValidationResult";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  useDeleteExternalVariable,
  useDownloadExternalTemplate,
  useExternalVariableCoverage,
  useExternalVariables,
  useExternalVariableValues,
  useImportExternalValues,
  useSaveExternalVariable,
  useUpdateExternalValues,
  useValidateExternalValues,
} from "@/hooks/useExternalVariables";
import { useCan } from "@/hooks/usePermission";
import { useProducts } from "@/hooks/useProducts";
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
  // CR v3.5 §3.2: definisi hanya admin; import nilai bulanan (+ dry-run) admin & PPIC.
  const canDefine = useCan("extvar.define");
  const canImport = useCan("extvar.import");
  const [editing, setEditing] = useState<ExternalVariable | null>(null);
  const [open, setOpen] = useState(false);
  const [viewing, setViewing] = useState<ExternalVariable | null>(null);
  const values = useExternalVariableValues(viewing?.id ?? null);
  const { data: products } = useProducts();

  const updateValues = useUpdateExternalValues();
  // Nilai untuk tab "Nilai per periode" di dialog Ubah (21 Nov 2026).
  const editValues = useExternalVariableValues(open && editing && canImport ? editing.id : null);

  const onError = (e: Error) => toast.error(e.message);

  const definitionForm = (
    <ExternalVariableForm
      key={editing?.id ?? "new"}
      initial={editing ?? undefined}
      submitting={save.isPending}
      error={save.error?.message ?? null}
      onSubmit={(input) =>
        save.mutate(
          { id: editing?.id, input },
          {
            onSuccess: () => {
              setOpen(false);
              toast.success(editing ? `Variabel ${editing.code} diperbarui` : "Variabel ditambahkan");
            },
          },
        )
      }
    />
  );

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
            {canImport && (
              <>
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
              </>
            )}
            {canDefine && (
              <Button
                onClick={() => {
                  setEditing(null);
                  setOpen(true);
                }}
              >
                <Plus />
                Tambah variabel
              </Button>
            )}
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
          onToggle={canDefine ? (v, next) => save.mutate({ id: v.id, input: { is_active: next } }, { onError }) : undefined}
          onEdit={
            canDefine || canImport
              ? (v) => {
                  setEditing(v);
                  setOpen(true);
                }
              : undefined
          }
          onClearValues={canDefine ? (v) => remove.mutate({ id: v.id, valuesOnly: true }, { onError }) : undefined}
          onDelete={canDefine ? (v) => remove.mutate({ id: v.id }, { onError }) : undefined}
          onViewValues={setViewing}
        />
      )}

      <Dialog open={viewing !== null} onOpenChange={(o) => !o && setViewing(null)}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Nilai {viewing?.code}</DialogTitle>
            <DialogDescription>
              {viewing?.name}
              {viewing?.unit ? ` (${viewing.unit})` : ""} — nilai per periode bulanan, terbaru di atas.
            </DialogDescription>
          </DialogHeader>
          {values.isPending ? (
            <TableSkeleton />
          ) : values.isError ? (
            <Alert variant="destructive">
              <AlertDescription>{values.error.message}</AlertDescription>
            </Alert>
          ) : (
            viewing && (
              <ExternalVariableValuesTable values={values.data ?? []} scope={viewing.scope} products={products ?? []} />
            )
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="flex max-h-[90vh] flex-col gap-0 p-0 sm:max-w-2xl">
          <DialogHeader className="border-b px-6 pb-4 pt-6">
            <DialogTitle>{editing ? `Ubah ${editing.code}` : "Tambah variabel eksternal"}</DialogTitle>
            <DialogDescription>
              {editing
                ? `${editing.name}${editing.unit ? ` (${editing.unit})` : ""} — ubah definisi atau nilai per periode.`
                : "Kode dipakai sebagai nama fitur model dan tidak bisa diubah setelah dibuat."}
            </DialogDescription>
          </DialogHeader>
          <div className="min-h-0 flex-1 overflow-y-auto px-6 py-4">
            {editing ? (
              <Tabs key={editing.id} defaultValue={canDefine ? "definition" : "values"}>
                <TabsList className="mb-4 grid w-full grid-cols-2">
                  <TabsTrigger value="definition" disabled={!canDefine}>
                    Definisi
                  </TabsTrigger>
                  <TabsTrigger value="values" disabled={!canImport}>
                    Nilai per periode{editing.n_values ? ` (${editing.n_values})` : ""}
                  </TabsTrigger>
                </TabsList>
                {canDefine && <TabsContent value="definition">{definitionForm}</TabsContent>}
                {canImport && (
                  <TabsContent value="values">
                    {editValues.isPending ? (
                      <TableSkeleton />
                    ) : editValues.isError ? (
                      <Alert variant="destructive">
                        <AlertDescription>{editValues.error.message}</AlertDescription>
                      </Alert>
                    ) : (
                      <ExternalVariableValuesEditor
                        key={editValues.dataUpdatedAt}
                        values={editValues.data ?? []}
                        valueType={editing.value_type}
                        scope={editing.scope}
                        products={products ?? []}
                        saving={updateValues.isPending}
                        error={updateValues.error?.message ?? null}
                        onSave={(items) =>
                          updateValues.mutate(
                            { id: editing.id, values: items },
                            { onSuccess: (r) => toast.success(`${r.updated} nilai ${editing.code} disimpan`) },
                          )
                        }
                      />
                    )}
                  </TabsContent>
                )}
              </Tabs>
            ) : (
              definitionForm
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
