"use client";

import { EmptyState } from "@/components/common/EmptyState";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatMoney, formatNumber, formatPercent } from "@/lib/format";
import type { Material } from "@/types/material";
import type { CostSummary, InventoryMetric, MetricScope } from "@/types/metrics";
import type { Product } from "@/types/product";
import type { ReorderRecommendation } from "@/types/reorder";

// 23 Nov 2026 — langkah "4. Evaluasi usulan inventory" (White Box tahap 5 thesis): existing (planning
// perusahaan) vs usulan ForecastIQ untuk fulfilment rate (service level), stockout rate, inventory
// turnover, holding cost, ordering cost & shortage cost. Metrik per material dihitung backend
// (inventory_metrics_service); di sini hanya rata-rata antar material untuk ringkasan. Biaya total
// dari cost-summary (TIC baseline dirinci pesan + simpan).

const num = (v: string | number | null | undefined): number | null => {
  if (v === null || v === undefined || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
};

const mean = (values: (number | null)[]): number | null => {
  const xs = values.filter((v): v is number => v !== null);
  return xs.length ? xs.reduce((s, v) => s + v, 0) / xs.length : null;
};

const ratio = (v: number | null) => (v === null ? "—" : formatPercent(v * 100, 1));
const times = (v: number | null) => (v === null ? "—" : `${formatNumber(v, 2)}×`);
const money = (v: number | null) => (v === null ? "—" : formatMoney(v));

type Kind = "ratio" | "times" | "money";

interface SummaryRow {
  label: string;
  hint: string;
  kind: Kind;
  higherIsBetter: boolean;
  baseline: number | null;
  proposed: number | null;
  extra?: string;
}

function formatValue(kind: Kind, v: number | null) {
  return kind === "ratio" ? ratio(v) : kind === "times" ? times(v) : money(v);
}

function formatDiff(kind: Kind, diff: number) {
  const sign = diff > 0 ? "+" : diff < 0 ? "−" : "";
  const abs = Math.abs(diff);
  if (kind === "ratio") return `${sign}${formatNumber(abs * 100, 1)} pp`;
  if (kind === "times") return `${sign}${formatNumber(abs, 2)}×`;
  return `${sign}${formatMoney(abs)}`;
}

function Verdict({ row }: { row: SummaryRow }) {
  if (row.baseline === null || row.proposed === null) return <span className="text-muted-foreground">—</span>;
  const diff = row.proposed - row.baseline;
  const better = row.higherIsBetter ? diff > 0 : diff < 0;
  const same = Math.abs(diff) < 1e-9;
  return (
    <span className="flex flex-wrap items-center justify-end gap-2">
      <span className="tabular-nums">{formatDiff(row.kind, diff)}</span>
      {same ? (
        <Badge variant="secondary">sama</Badge>
      ) : (
        <Badge variant={better ? "success" : "destructive"}>{better ? "lebih baik" : "lebih buruk"}</Badge>
      )}
    </span>
  );
}

interface Props {
  metrics: InventoryMetric[];
  cost?: CostSummary | null;
  recommendations: ReorderRecommendation[];
  materials: Material[];
  products: Product[];
}

export function InventoryEvaluation({ metrics, cost, recommendations, materials }: Props) {
  if (metrics.length === 0) {
    return (
      <EmptyState message="Belum ada metrik evaluasi untuk run ini." hint="Jalankan ulang perencanaan untuk menghitungnya." />
    );
  }

  const materialMetrics = metrics.filter((m) => m.target_type === "material");
  const byScope = (scope: MetricScope) => materialMetrics.filter((m) => m.scope === scope);
  const avg = (scope: MetricScope, f: (m: InventoryMetric) => string | null | undefined) =>
    mean(byScope(scope).map((m) => num(f(m))));

  const rows: SummaryRow[] = [
    {
      label: "Fulfilment rate (β) — service level",
      hint: "1 − Σ kekurangan ÷ Σ pemakaian (berbasis qty), rata-rata material",
      kind: "ratio",
      higherIsBetter: true,
      baseline: avg("baseline", (m) => m.fill_rate),
      proposed: avg("forecastiq", (m) => m.fill_rate),
    },
    {
      label: "Service level (α)",
      hint: "1 − stockout rate (berbasis periode), rata-rata material",
      kind: "ratio",
      higherIsBetter: true,
      baseline: avg("baseline", (m) => m.service_level),
      proposed: avg("forecastiq", (m) => m.service_level),
    },
    {
      label: "Stockout rate",
      hint: "periode kekurangan ÷ jumlah periode, rata-rata material",
      kind: "ratio",
      higherIsBetter: false,
      baseline: avg("baseline", (m) => m.stock_out_rate),
      proposed: avg("forecastiq", (m) => m.stock_out_rate),
    },
    {
      label: "Inventory turnover",
      hint: "pemakaian ÷ rata-rata persediaan, rata-rata material",
      kind: "times",
      higherIsBetter: true,
      baseline: avg("baseline", (m) => m.inventory_turnover),
      proposed: avg("forecastiq", (m) => m.inventory_turnover),
    },
    {
      label: "Ordering cost (biaya pesan)",
      hint: "Σ material, per tahun: (A ÷ Q) × S",
      kind: "money",
      higherIsBetter: false,
      baseline: num(cost?.baseline_ordering_cost),
      proposed: num(cost?.total_ordering_cost),
    },
    {
      label: "Holding cost (biaya simpan)",
      hint: "Σ material, per tahun: (Q ÷ 2) × i × C (klasik) atau Σ stok akhir × H (dinamis)",
      kind: "money",
      higherIsBetter: false,
      baseline: num(cost?.baseline_holding_cost),
      proposed: num(cost?.total_holding_cost),
    },
    {
      label: "Shortage cost (biaya kekurangan)",
      hint: "Σ qty produk tak terpenuhi × harga produk",
      kind: "money",
      higherIsBetter: false,
      baseline: num(cost?.baseline_shortage_cost),
      proposed: num(cost?.shortage_cost),
    },
    {
      label: "Total biaya persediaan (TIC)",
      hint: "ordering cost + holding cost",
      kind: "money",
      higherIsBetter: false,
      baseline: num(cost?.baseline_inventory_cost),
      proposed: num(cost?.total_inventory_cost),
      extra: cost?.savings_pct != null ? `penghematan ${formatPercent(cost.savings_pct, 1)}` : undefined,
    },
  ];

  const materialById = new Map(materials.map((m) => [m.id, m]));
  const recById = new Map(recommendations.map((r) => [r.material_id, r]));
  const metricOf = new Map(materialMetrics.map((m) => [`${m.target_id}:${m.scope}`, m]));
  const materialIds = [...new Set(materialMetrics.map((m) => m.target_id))].sort((a, b) =>
    (materialById.get(a)?.code ?? a).localeCompare(materialById.get(b)?.code ?? b),
  );
  const pair = (id: string, f: (m: InventoryMetric) => string | null | undefined, fmt: (v: number | null) => string) =>
    (["baseline", "forecastiq"] as const).map((scope) => {
      const m = metricOf.get(`${id}:${scope}`);
      return (
        <TableCell key={scope} className="text-right tabular-nums">
          {fmt(m ? num(f(m)) : null)}
        </TableCell>
      );
    });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <h3 className="font-medium">Ringkasan: existing vs usulan ForecastIQ</h3>
        <p className="text-sm text-muted-foreground">
          Existing = pemakaian dari planning perusahaan; usulan = pemakaian dari forecast ForecastIQ dengan kebijakan
          pesan hasil perencanaan (SS, buffer, EOQ, ROP).
        </p>
        <div className="overflow-x-auto rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Indikator</TableHead>
                <TableHead className="text-right">Existing (planning)</TableHead>
                <TableHead className="text-right">Usulan ForecastIQ</TableHead>
                <TableHead className="text-right">Selisih</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((r) => (
                <TableRow key={r.label}>
                  <TableCell>
                    <span className="font-medium">{r.label}</span>
                    <span className="block text-xs text-muted-foreground">{r.hint}</span>
                  </TableCell>
                  <TableCell className="text-right tabular-nums">{formatValue(r.kind, r.baseline)}</TableCell>
                  <TableCell className="text-right tabular-nums">
                    {formatValue(r.kind, r.proposed)}
                    {r.extra && <span className="block text-xs text-muted-foreground">{r.extra}</span>}
                  </TableCell>
                  <TableCell className="text-right">
                    <Verdict row={r} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>

      {materialIds.length > 0 && (
        <div className="flex flex-col gap-2">
          <h3 className="font-medium">Rincian per material</h3>
          <p className="text-sm text-muted-foreground">
            E = existing (planning), U = usulan ForecastIQ. Biaya pesan & simpan per material tersedia untuk usulan
            (dari rekomendasi reorder); baseline hanya total di ringkasan.
          </p>
          <div className="overflow-x-auto rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Material</TableHead>
                  <TableHead className="text-right">Fulfilment rate E</TableHead>
                  <TableHead className="text-right">Fulfilment rate U</TableHead>
                  <TableHead className="text-right">Stockout E</TableHead>
                  <TableHead className="text-right">Stockout U</TableHead>
                  <TableHead className="text-right">Turnover E</TableHead>
                  <TableHead className="text-right">Turnover U</TableHead>
                  <TableHead className="text-right">Ordering cost U</TableHead>
                  <TableHead className="text-right">Holding cost U</TableHead>
                  <TableHead className="text-right">Shortage cost E</TableHead>
                  <TableHead className="text-right">Shortage cost U</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {materialIds.map((id) => {
                  const m = materialById.get(id);
                  const rec = recById.get(id);
                  return (
                    <TableRow key={id}>
                      <TableCell className="whitespace-nowrap">{m ? `${m.code} — ${m.name}` : id}</TableCell>
                      {pair(id, (x) => x.fill_rate, ratio)}
                      {pair(id, (x) => x.stock_out_rate, ratio)}
                      {pair(id, (x) => x.inventory_turnover, times)}
                      <TableCell className="text-right tabular-nums">{money(num(rec?.ordering_cost))}</TableCell>
                      <TableCell className="text-right tabular-nums">{money(num(rec?.holding_cost))}</TableCell>
                      {pair(id, (x) => x.shortage_cost, money)}
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        </div>
      )}
    </div>
  );
}
