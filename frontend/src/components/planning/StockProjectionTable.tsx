"use client";

import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDate, formatNumber } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Material } from "@/types/material";
import type { ProjectionScenario, StockProjectionRow } from "@/types/planning";

const SCENARIOS: { value: ProjectionScenario; label: string }[] = [
  { value: "proposed", label: "Usulan (forecast)" },
  { value: "baseline", label: "Existing (planning)" },
];

function Utilization({ pct }: { pct: number | null }) {
  if (pct == null) return <span className="text-muted-foreground">—</span>;
  return (
    <span className="flex items-center gap-2">
      <span className="h-2 w-16 rounded-full bg-muted">
        <span
          className={cn("block h-2 rounded-full", pct > 100 ? "bg-destructive" : "bg-primary")}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </span>
      <span className="tabular-nums">{pct.toFixed(1)}%</span>
    </span>
  );
}

// Tahap 3 thesis (Fase 11.6): stok awal + kedatangan + pesanan − pemakaian = stok akhir,
// utilisasi gudang material per periode. Satu tabel per material; tab memilih skenario.
export function StockProjectionTable({ rows, materials = [] }: { rows: StockProjectionRow[]; materials?: Material[] }) {
  const [scenario, setScenario] = useState<ProjectionScenario>("proposed");
  const hasBaseline = rows.some((r) => r.scenario === "baseline");
  const byMaterial = new Map<string, StockProjectionRow[]>();
  for (const r of rows.filter((x) => x.scenario === scenario)) {
    byMaterial.set(r.material_id, [...(byMaterial.get(r.material_id) ?? []), r]);
  }
  const label = new Map(materials.map((m) => [m.id, `${m.code} — ${m.name}`]));

  return (
    <div className="flex flex-col gap-4">
      <div role="tablist" className="inline-flex w-fit rounded-lg bg-muted p-1">
        {SCENARIOS.map((s) => (
          <button
            key={s.value}
            type="button"
            role="tab"
            aria-selected={scenario === s.value}
            disabled={s.value === "baseline" && !hasBaseline}
            onClick={() => setScenario(s.value)}
            className={cn(
              "rounded-md px-3 py-1 text-sm disabled:opacity-50",
              scenario === s.value && "bg-background shadow-sm",
            )}
          >
            {s.label}
          </button>
        ))}
      </div>
      {!hasBaseline && (
        <p className="text-xs text-muted-foreground">
          Skenario existing butuh data planning perusahaan untuk seluruh periode horizon.
        </p>
      )}

      {[...byMaterial.entries()].map(([materialId, list]) => (
        <div key={materialId} className="flex flex-col gap-2">
          <p className="text-sm font-medium">{label.get(materialId) ?? materialId}</p>
          <div className="overflow-x-auto rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Periode</TableHead>
                  <TableHead>Stok awal</TableHead>
                  <TableHead>Kedatangan</TableHead>
                  <TableHead>Pesanan (EOQ)</TableHead>
                  <TableHead>Pemakaian</TableHead>
                  <TableHead>Stok akhir</TableHead>
                  <TableHead>Kekurangan</TableHead>
                  <TableHead>Utilisasi awal</TableHead>
                  <TableHead>Utilisasi akhir</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {list.map((r) => (
                  <TableRow key={r.period}>
                    <TableCell>{formatDate(r.period)}</TableCell>
                    <TableCell className="tabular-nums">{formatNumber(r.opening_qty)}</TableCell>
                    <TableCell className="tabular-nums">{formatNumber(r.receipt_qty)}</TableCell>
                    <TableCell className="tabular-nums">{formatNumber(r.order_qty)}</TableCell>
                    <TableCell className="tabular-nums">{formatNumber(r.usage_qty)}</TableCell>
                    <TableCell className="tabular-nums">{formatNumber(r.ending_qty)}</TableCell>
                    <TableCell className="tabular-nums">
                      {r.shortage_qty > 0 ? (
                        <span className="text-destructive">{formatNumber(r.shortage_qty)}</span>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                    <TableCell>
                      <Utilization pct={r.utilization_opening_pct} />
                    </TableCell>
                    <TableCell>
                      <span className="flex flex-wrap items-center gap-2">
                        <Utilization pct={r.utilization_ending_pct} />
                        {r.is_within_capacity === false && <Badge variant="destructive">Melebihi kapasitas</Badge>}
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      ))}
    </div>
  );
}
