"use client";

import { Plus, X } from "lucide-react";
import { useMemo, useState } from "react";

import { EmptyState } from "@/components/common/EmptyState";
import { FormError } from "@/components/common/FormError";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { type EditableValueRow, valueChanges } from "@/lib/externalVariable";
import { formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";
import type {
  ExternalScope,
  ExternalValueType,
  ExternalVariableValue,
  ExternalVariableValueChange,
} from "@/types/externalVariable";
import type { Product } from "@/types/product";

const toText = (n: number) => String(n).replace(".", ",");

// 21 Nov 2026 — dialog "Ubah" bisa mengubah nilai per periode (PUT /external-variables/{id}/values),
// bukan hanya definisi. Nilai tersimpan bisa diedit; periode baru bisa ditambah. Hanya baris yang
// berubah yang dikirim.
export function ExternalVariableValuesEditor({
  values,
  valueType,
  scope,
  products,
  onSave,
  saving,
  error,
}: {
  values: ExternalVariableValue[];
  valueType: ExternalValueType;
  scope: ExternalScope;
  products: Product[];
  onSave: (items: ExternalVariableValueChange[]) => void;
  saving?: boolean;
  error?: string | null;
}) {
  const perProduct = scope === "product";
  const code = useMemo(() => new Map(products.map((p) => [p.id, p.code])), [products]);
  const [rows, setRows] = useState<EditableValueRow[]>(() =>
    [...values]
      .sort(
        (a, b) =>
          b.period.localeCompare(a.period) ||
          (code.get(a.product_id ?? "") ?? "").localeCompare(code.get(b.product_id ?? "") ?? ""),
      )
      .map((v) => ({ period: v.period, product_id: v.product_id, value: toText(v.value), original: toText(v.value) })),
  );
  const [errors, setErrors] = useState<string[]>([]);

  const { items } = valueChanges(rows, { value_type: valueType, scope });
  const nNew = rows.filter((r) => r.original === null).length;
  const dirty = rows.some((r) => (r.original === null ? r.value.trim() || r.period : r.value.trim() !== r.original));

  const patch = (i: number, change: Partial<EditableValueRow>) =>
    setRows((rs) => rs.map((r, j) => (j === i ? { ...r, ...change } : r)));

  const submit = () => {
    const result = valueChanges(rows, { value_type: valueType, scope });
    setErrors(result.errors);
    if (!result.errors.length && result.items.length) onSave(result.items);
  };

  let newIndex = 0;
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-muted-foreground">
          {valueType === "flag" ? "Isi 0 atau 1." : "Koma desimal diterima."} Periode baru otomatis disimpan sebagai
          awal bulan; periode yang sudah ada akan ditimpa.
        </p>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setRows((rs) => [{ period: "", product_id: null, value: "", original: null }, ...rs])}
        >
          <Plus />
          Tambah periode
        </Button>
      </div>

      {rows.length === 0 ? (
        <EmptyState message="Belum ada nilai." hint="Tambah periode di sini atau lewat Import nilai." />
      ) : (
        <div className="max-h-[45vh] overflow-auto rounded-lg border">
          <Table>
            <TableHeader className="sticky top-0 z-10 bg-background">
              <TableRow>
                <TableHead className="w-44">Periode</TableHead>
                {perProduct && <TableHead>Produk</TableHead>}
                <TableHead className="w-40">Nilai</TableHead>
                <TableHead className="w-10">
                  <span className="sr-only">Aksi</span>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((r, i) => {
                const isNew = r.original === null;
                const n = isNew ? ++newIndex : 0;
                const label = isNew ? `baris baru ${n}` : r.period.slice(0, 7);
                const changed = !isNew && r.value.trim() !== r.original;
                return (
                  <TableRow
                    key={isNew ? `new-${nNew - n}` : `${r.period}-${r.product_id ?? "global"}`}
                    className={cn((isNew || changed) && "bg-primary/5")}
                  >
                    <TableCell>
                      {isNew ? (
                        <Input
                          type="month"
                          aria-label={`Periode ${label}`}
                          value={r.period.slice(0, 7)}
                          onChange={(e) => patch(i, { period: e.target.value })}
                          className="h-8"
                        />
                      ) : (
                        formatDate(r.period)
                      )}
                    </TableCell>
                    {perProduct && (
                      <TableCell>
                        {isNew ? (
                          <select
                            aria-label={`Produk ${label}`}
                            value={r.product_id ?? ""}
                            onChange={(e) => patch(i, { product_id: e.target.value || null })}
                            className="h-8 w-full rounded-md border border-input bg-transparent px-2 text-sm"
                          >
                            <option value="">Pilih produk…</option>
                            {products.map((p) => (
                              <option key={p.id} value={p.id}>
                                {p.code}
                              </option>
                            ))}
                          </select>
                        ) : r.product_id ? (
                          (code.get(r.product_id) ?? r.product_id)
                        ) : (
                          "—"
                        )}
                      </TableCell>
                    )}
                    <TableCell>
                      <Input
                        inputMode="decimal"
                        aria-label={`Nilai ${label}`}
                        value={r.value}
                        onChange={(e) => patch(i, { value: e.target.value })}
                        className="h-8 tabular-nums"
                      />
                    </TableCell>
                    <TableCell>
                      {isNew ? (
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="size-7"
                          aria-label={`Batalkan ${label}`}
                          onClick={() => setRows((rs) => rs.filter((_, j) => j !== i))}
                        >
                          <X />
                        </Button>
                      ) : (
                        changed && (
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="size-7"
                            aria-label={`Kembalikan ${label}`}
                            onClick={() => patch(i, { value: r.original as string })}
                          >
                            <X />
                          </Button>
                        )
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}

      {errors.length > 0 && (
        <ul className="flex list-disc flex-col gap-0.5 pl-5 text-sm text-destructive">
          {errors.slice(0, 10).map((e) => (
            <li key={e}>{e}</li>
          ))}
          {errors.length > 10 && <li>+{errors.length - 10} error lain</li>}
        </ul>
      )}
      <FormError message={error ?? null} />

      <div className="flex items-center justify-end gap-3">
        {items.length > 0 && <span className="text-xs text-muted-foreground">{items.length} nilai akan disimpan</span>}
        <Button type="button" onClick={submit} disabled={saving || !dirty}>
          {saving ? "Menyimpan…" : "Simpan nilai"}
        </Button>
      </div>
    </div>
  );
}
