"use client";

import { EmptyState } from "@/components/common/EmptyState";
import { LeadTimeWarning } from "@/components/common/LeadTimeWarning";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDate, formatNumber } from "@/lib/format";
import { exceedsOnePeriod, LEAD_TIME_PERIOD_DAYS } from "@/lib/leadTime";
import type { Material } from "@/types/material";
import type { StockProjectionRow } from "@/types/planning";
import type { ReorderRecommendation } from "@/types/reorder";

const POLICY_LABEL: Record<string, string> = {
  order_up_to: "Order-up-to (S − stok)",
  eoq: "n × EOQ",
};

// Kedatangan material = pesanan hasil ROP di proyeksi stok skenario usulan (20 Nov 2026).
// Pesan bila stok sebelum pesan (stok awal − pemakaian) ≤ ROP; qty sesuai kebijakan di
// Pengaturan Forecast; diasumsikan tiba di periode yang sama (lead time < 1 periode, asumsi
// thesis). Read-only: tidak ada lagi input/upload kedatangan manual.
export function MaterialArrivalsTable({
  rows,
  recommendations = [],
  materials = [],
}: {
  rows: StockProjectionRow[];
  recommendations?: ReorderRecommendation[];
  materials?: Material[];
}) {
  const label = new Map(materials.map((m) => [m.id, `${m.code} — ${m.name}`]));
  const code = new Map(materials.map((m) => [m.id, m.code]));
  const leadTime = new Map(materials.map((m) => [m.id, m.lead_time_days]));
  const rec = new Map(recommendations.map((r) => [r.material_id, r]));
  const arrivals = rows
    .filter((r) => r.scenario === "proposed" && r.order_qty > 0)
    .sort(
      (a, b) =>
        a.period.localeCompare(b.period) ||
        (code.get(a.material_id) ?? a.material_id).localeCompare(code.get(b.material_id) ?? b.material_id),
    );

  if (arrivals.length === 0) {
    return (
      <EmptyState
        message="Tidak ada kedatangan material di horizon ini."
        hint="Stok sebelum pesan tidak pernah turun ke ROP pada skenario usulan."
      />
    );
  }

  const arrivingMaterials = new Set(arrivals.map((r) => r.material_id));
  const nMaterials = arrivingMaterials.size;
  const nLongLead = [...arrivingMaterials].filter((id) => exceedsOnePeriod(leadTime.get(id))).length;

  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm text-muted-foreground">
        {arrivals.length} kedatangan dari {nMaterials} material
      </p>
      {nLongLead > 0 && (
        <p className="text-sm text-warning">
          {nLongLead} material dengan lead time ≥ {LEAD_TIME_PERIOD_DAYS} hari — asumsi kedatangan di periode yang
          sama tidak berlaku untuk material tersebut (batasan model), periksa jadwal pesannya secara manual.
        </p>
      )}
      <div className="overflow-x-auto rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Periode tiba</TableHead>
              <TableHead>Material</TableHead>
              <TableHead>Stok sebelum pesan</TableHead>
              <TableHead>ROP</TableHead>
              <TableHead>Qty tiba</TableHead>
              <TableHead>Kebijakan qty</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {arrivals.map((r) => {
              const policy = rec.get(r.material_id)?.order_qty_policy_used;
              return (
                <TableRow key={`${r.material_id}-${r.period}`}>
                  <TableCell>{formatDate(r.period)}</TableCell>
                  <TableCell>
                    <span className="flex flex-wrap items-center gap-2">
                      {label.get(r.material_id) ?? r.material_id}
                      {exceedsOnePeriod(leadTime.get(r.material_id)) && (
                        <LeadTimeWarning leadTimeDays={leadTime.get(r.material_id) as number} />
                      )}
                    </span>
                  </TableCell>
                  <TableCell className="tabular-nums">{formatNumber(r.opening_qty - r.usage_qty)}</TableCell>
                  <TableCell className="tabular-nums">{formatNumber(rec.get(r.material_id)?.reorder_point ?? null)}</TableCell>
                  <TableCell className="font-medium tabular-nums">{formatNumber(r.order_qty)}</TableCell>
                  <TableCell>{policy ? (POLICY_LABEL[policy] ?? policy) : "—"}</TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
