"use client";

import { AlertTriangle, Info } from "lucide-react";
import { useEffect, useState } from "react";

import { FormError } from "@/components/common/FormError";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { useResetCapacityAdjustments, useSaveCapacityAdjustments } from "@/hooks/usePlanning";
import { formatNumber, formatPercent } from "@/lib/format";
import type { Material } from "@/types/material";
import type { CapacitySuggestion, OverflowCause } from "@/types/planning";

const CAUSE_LABEL: Record<OverflowCause, string> = {
  opening_stock: "Stok awal (snapshot ERP) sudah melebihi kapasitas",
  receipts: "Kedatangan terjadwal membuat gudang penuh",
  moq: "Qty pesan minimum (MOQ) lebih besar dari ruang tersisa",
  cycle_stock: "Pemakaian selama lead time (cycle stock) — perlu kurangi EOQ / tambah kapasitas",
};

function arrow(before: number | null, after: number | null, fmt: (v: number | null) => string) {
  return `${fmt(before)} → ${fmt(after)}`;
}

const qty = (v: number | null) => formatNumber(v);
const pct = (v: number | null) => formatPercent(v, 1);

// Fase 11.17 — loop kapasitas gudang: stok akhir proyeksi melebihi kapasitas grup material →
// sistem mengusulkan SS (turunkan service level) & Buffer. Planner menerima usulan atau mengisi
// angka custom (alasan wajib), lalu perencanaan dijalankan ulang (kembali ke tahap 2).
export function CapacityAdjustmentPanel({
  runId,
  suggestion,
  adjustedCount,
  materials = [],
  onReplan,
}: {
  runId: string;
  suggestion: CapacitySuggestion | null | undefined;
  adjustedCount: number;
  materials?: Material[];
  onReplan: () => void;
}) {
  const save = useSaveCapacityAdjustments(runId);
  const reset = useResetCapacityAdjustments(runId);
  const active = suggestion && suggestion.status !== "within_capacity" ? suggestion : null;
  const items = active?.items ?? [];
  const [custom, setCustom] = useState<Record<string, { ss: string; buffer: string }>>({});
  // Isian custom = usulan terbaru; diisi ulang setiap usulan berubah (setelah perencanaan diulang).
  useEffect(() => {
    setCustom(
      Object.fromEntries(
        (suggestion?.items ?? []).map((i) => [
          i.material_id,
          { ss: String(i.safety_stock_after), buffer: String(i.buffer_stock_after) },
        ]),
      ),
    );
  }, [suggestion]);
  const [reason, setReason] = useState("");
  const [reasonError, setReasonError] = useState<string | null>(null);

  if (!active && adjustedCount === 0) return null;

  const code = new Map(materials.map((m) => [m.id, m.code]));
  const label = new Map(materials.map((m) => [m.id, `${m.code} — ${m.name}`]));
  const busy = save.isPending || reset.isPending;

  const accept = () => {
    save.mutate(
      {
        source: "suggested",
        items: items.map((i) => ({
          material_id: i.material_id,
          safety_stock: i.safety_stock_after,
          buffer_stock: i.buffer_stock_after,
          service_level_pct: i.service_level_pct,
        })),
        reason: null,
      },
      { onSuccess: onReplan },
    );
  };

  const saveCustom = () => {
    if (!reason.trim()) {
      setReasonError("Alasan wajib diisi");
      return;
    }
    setReasonError(null);
    save.mutate(
      {
        source: "custom",
        items: items.map((i) => ({
          material_id: i.material_id,
          safety_stock: Number(custom[i.material_id]?.ss ?? i.safety_stock_after),
          buffer_stock: Number(custom[i.material_id]?.buffer ?? i.buffer_stock_after),
        })),
        reason: reason.trim(),
      },
      { onSuccess: onReplan },
    );
  };

  const setField = (mid: string, field: "ss" | "buffer", value: string) =>
    setCustom((prev) => ({ ...prev, [mid]: { ...(prev[mid] ?? { ss: "", buffer: "" }), [field]: value } }));

  return (
    <div className="flex flex-col gap-4 rounded-lg border p-4">
      {active && (
        <Alert variant={active.status === "infeasible" ? "destructive" : "default"}>
          <AlertTriangle className="size-4" />
          <AlertTitle>
            {active.status === "infeasible"
              ? "Adjust SS & Buffer tidak cukup — masih ada grup yang overload"
              : "Stok proyeksi melebihi kapasitas gudang"}
          </AlertTitle>
          <AlertDescription>
            Usulan sistem: turunkan service level SS (batas bawah 90%), lalu potong Buffer proporsional. ROP ikut
            dihitung ulang. Skenario existing (planning) tidak diubah.
          </AlertDescription>
        </Alert>
      )}

      {active && (
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Grup</TableHead>
                <TableHead className="text-right">Kapasitas</TableHead>
                <TableHead className="text-right">Kelebihan (sebelum → sesudah)</TableHead>
                <TableHead>Service level</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {active.groups.map((g) => (
                <TableRow key={g.group}>
                  <TableCell className="font-medium">{g.group}</TableCell>
                  <TableCell className="text-right tabular-nums">{qty(g.capacity_qty)}</TableCell>
                  <TableCell className="text-right tabular-nums">{arrow(g.excess_before, g.excess_after, qty)}</TableCell>
                  <TableCell className="tabular-nums">{arrow(active.target_service_level_pct, g.service_level_pct, pct)}</TableCell>
                  <TableCell>
                    {g.status === "infeasible" ? (
                      <div className="flex flex-col gap-1">
                        <Badge variant="destructive" className="w-fit">Tidak muat</Badge>
                        {g.cause && <span className="text-xs text-muted-foreground">{CAUSE_LABEL[g.cause]}</span>}
                      </div>
                    ) : (
                      <Badge variant="secondary">Muat setelah adjust</Badge>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {items.length > 0 && (
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Material</TableHead>
                <TableHead className="text-right">SS (sistem → usulan)</TableHead>
                <TableHead className="text-right">Buffer (sistem → usulan)</TableHead>
                <TableHead className="text-right">ROP (sistem → usulan)</TableHead>
                <TableHead className="text-right">α efektif</TableHead>
                <TableHead>SS custom</TableHead>
                <TableHead>Buffer custom</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((i) => {
                const name = code.get(i.material_id) ?? i.material_id;
                return (
                  <TableRow key={i.material_id}>
                    <TableCell className="font-medium">{label.get(i.material_id) ?? i.material_id}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {arrow(i.safety_stock_before, i.safety_stock_after, qty)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {arrow(i.buffer_stock_before, i.buffer_stock_after, qty)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {arrow(i.reorder_point_before, i.reorder_point_after, qty)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {arrow(i.service_level_before, i.service_level_after, pct)}
                    </TableCell>
                    <TableCell>
                      <Input
                        aria-label={`SS custom ${name}`}
                        type="number"
                        min={0}
                        step="any"
                        className="w-28"
                        value={custom[i.material_id]?.ss ?? ""}
                        onChange={(e) => setField(i.material_id, "ss", e.target.value)}
                      />
                    </TableCell>
                    <TableCell>
                      <Input
                        aria-label={`Buffer custom ${name}`}
                        type="number"
                        min={0}
                        step="any"
                        className="w-28"
                        value={custom[i.material_id]?.buffer ?? ""}
                        onChange={(e) => setField(i.material_id, "buffer", e.target.value)}
                      />
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}

      {items.length > 0 && (
        <div className="flex flex-col gap-2">
          <Label htmlFor="cap-adj-reason">Alasan adjust custom</Label>
          <Textarea
            id="cap-adj-reason"
            className="min-h-16"
            aria-invalid={reasonError ? true : undefined}
            aria-describedby={reasonError ? "cap-adj-reason-error" : undefined}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
          {reasonError && (
            <p id="cap-adj-reason-error" className="text-sm font-medium text-destructive">
              {reasonError}
            </p>
          )}
        </div>
      )}

      {adjustedCount > 0 && (
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <Info className="size-4" />
          {adjustedCount} material memakai adjust kapasitas (SS/Buffer) — nilai sistem tetap tersimpan.
        </p>
      )}

      <FormError message={save.isError ? save.error.message : reset.isError ? reset.error.message : null} />

      <div className="flex flex-wrap gap-2">
        {items.length > 0 && (
          <>
            <Button disabled={busy} onClick={accept}>
              {save.isPending ? "Menyimpan…" : "Terima usulan & jalankan ulang"}
            </Button>
            <Button variant="outline" disabled={busy} onClick={saveCustom}>
              Simpan custom & jalankan ulang
            </Button>
          </>
        )}
        {adjustedCount > 0 && (
          <Button variant="ghost" disabled={busy} onClick={() => reset.mutate(undefined, { onSuccess: onReplan })}>
            Kembali ke nilai sistem
          </Button>
        )}
      </div>
    </div>
  );
}
