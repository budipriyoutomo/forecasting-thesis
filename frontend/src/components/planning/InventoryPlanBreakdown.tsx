"use client";

import { ITEM_STATUS_NOTE, ROP_FORMULA_LABEL } from "@/components/dashboard/ReorderDetail";
import { STATUS_LABEL, STATUS_VARIANT } from "@/components/dashboard/ReorderTable";
import { StockProjectionTable, Utilization } from "@/components/planning/StockProjectionTable";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { formatDate, formatMoney, formatNumber, formatPercent, formatQty } from "@/lib/format";
import { materialGroupKey } from "@/lib/warehouse";
import type { Material } from "@/types/material";
import type { StockProjectionRow } from "@/types/planning";
import type { ReorderRecommendation } from "@/types/reorder";

// 23 Nov 2026 — langkah "3. Perencanaan persediaan": menampilkan PERHITUNGAN tiap tahap alur thesis
// (White Box tahap 2–4): MRP → SS & buffer → total kebutuhan → EOQ & kebijakan → ROP → kapasitas
// gudang per grup → simulasi stok. Semua angka hasil (SS, B, EOQ, ROP, qty, utilisasi) dibaca dari
// backend (`reorder_recommendations` & `stock_projections`); di sini hanya penjumlahan/penurunan
// tampilan (Σ, μ ÷ hari) — rumus ROP & qty pesan tetap hanya di reorder_service (AGENTS.md §11).

const num = (v: string | number | null | undefined): number | null => {
  if (v === null || v === undefined || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
};

const QTY_POLICY_LABEL: Record<string, string> = {
  eoq: "n × EOQ (kelipatan EOQ)",
  order_up_to: "Order-up-to: S − stok (min. MOQ)",
};

const NUM = "text-right tabular-nums";

interface Props {
  projection: StockProjectionRow[];
  recommendations: ReorderRecommendation[];
  materials: Material[];
}

export function InventoryPlanBreakdown({ projection, recommendations, materials }: Props) {
  const materialById = new Map(materials.map((m) => [m.id, m]));
  const recById = new Map(recommendations.map((r) => [r.material_id, r]));
  const proposed = projection.filter((r) => r.scenario === "proposed");
  const periods = [...new Set(proposed.map((r) => r.period))].sort();
  const rowsByMaterial = new Map<string, Map<string, StockProjectionRow>>();
  for (const r of proposed) {
    const m = rowsByMaterial.get(r.material_id) ?? new Map<string, StockProjectionRow>();
    m.set(r.period, r);
    rowsByMaterial.set(r.material_id, m);
  }
  const materialIds = [...new Set([...rowsByMaterial.keys(), ...recById.keys()])].sort((a, b) =>
    (materialById.get(a)?.code ?? a).localeCompare(materialById.get(b)?.code ?? b),
  );
  const label = (id: string) => {
    const m = materialById.get(id);
    return m ? `${m.code} — ${m.name}` : id;
  };
  const unit = (id: string) => materialById.get(id)?.unit;
  const mrpTotal = (id: string) => [...(rowsByMaterial.get(id)?.values() ?? [])].reduce((s, r) => s + r.usage_qty, 0);
  const missingInputs = recommendations.some((r) => r.mu_period == null);
  const policies = new Set(recommendations.map((r) => r.order_qty_policy_used).filter(Boolean));
  const ropFormulas = new Set(recommendations.map((r) => r.rop_formula_used).filter(Boolean));

  return (
    <div className="flex flex-col gap-3">
      {missingInputs && (
        <Alert variant="warning">
          <AlertDescription>
            Sebagian rekomendasi dihitung sebelum input perhitungan (μ, σ, Z, lead time, S, H) disimpan — jalankan
            ulang perencanaan untuk menampilkan rincian perhitungannya.
          </AlertDescription>
        </Alert>
      )}
      <Tabs defaultValue="mrp">
        <TabsList className="h-auto flex-wrap justify-start">
          <TabsTrigger value="mrp">1. MRP</TabsTrigger>
          <TabsTrigger value="ss">2. Safety &amp; buffer stock</TabsTrigger>
          <TabsTrigger value="total">3. Total kebutuhan</TabsTrigger>
          <TabsTrigger value="eoq">4. EOQ &amp; kebijakan</TabsTrigger>
          <TabsTrigger value="rop">5. Reorder point (ROP)</TabsTrigger>
          <TabsTrigger value="capacity">6. Kapasitas gudang</TabsTrigger>
          <TabsTrigger value="simulation">7. Simulasi stok</TabsTrigger>
        </TabsList>

        {/* 1. MRP per bulan per material */}
        <TabsContent value="mrp" className="flex flex-col gap-2">
          <Formula>MRP (kebutuhan kotor material) per periode = Σ produk (forecast produk × qty BOM per unit).</Formula>
          <ScrollTable>
            <TableHeader>
              <TableRow>
                <TableHead>Material</TableHead>
                {periods.map((p) => (
                  <TableHead key={p} className={NUM}>
                    {formatDate(p)}
                  </TableHead>
                ))}
                <TableHead className={NUM}>Total</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {[...rowsByMaterial.keys()]
                .sort((a, b) => label(a).localeCompare(label(b)))
                .map((id) => (
                  <TableRow key={id}>
                    <TableCell className="whitespace-nowrap">{label(id)}</TableCell>
                    {periods.map((p) => (
                      <TableCell key={p} className={NUM}>
                        {formatNumber(rowsByMaterial.get(id)?.get(p)?.usage_qty ?? null)}
                      </TableCell>
                    ))}
                    <TableCell className={`${NUM} font-medium`}>{formatQty(mrpTotal(id), unit(id))}</TableCell>
                  </TableRow>
                ))}
            </TableBody>
          </ScrollTable>
        </TabsContent>

        {/* 2. Safety stock & buffer stock */}
        <TabsContent value="ss" className="flex flex-col gap-2">
          <Formula>
            SS = Z × σ harian × √L, dengan σ harian = σ per periode ÷ √(hari per periode) dan Z = Φ⁻¹(service
            level). Buffer stock = max(0, faktor waste − 1) × μ kebutuhan per periode, faktor waste = Σ pemakaian
            aktual ÷ Σ pemakaian standar.
          </Formula>
          <ScrollTable>
            <TableHeader>
              <TableRow>
                <TableHead>Material</TableHead>
                <TableHead className={NUM}>μ / periode</TableHead>
                <TableHead className={NUM}>σ / periode</TableHead>
                <TableHead className={NUM}>σ harian</TableHead>
                <TableHead className={NUM}>Lead time (L)</TableHead>
                <TableHead className={NUM}>Z (service level)</TableHead>
                <TableHead className={NUM}>Safety stock</TableHead>
                <TableHead className={NUM}>Faktor waste</TableHead>
                <TableHead className={NUM}>Buffer stock</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {materialIds.map((id) => {
                const r = recById.get(id);
                if (!r) return null;
                const sigma = num(r.sigma_period);
                const days = num(r.period_days);
                const sigmaDaily = sigma !== null && days ? sigma / Math.sqrt(days) : null;
                const manual = materialById.get(id)?.manual_safety_stock != null;
                return (
                  <TableRow key={id}>
                    <TableCell className="whitespace-nowrap">{label(id)}</TableCell>
                    <TableCell className={NUM}>{formatNumber(r.mu_period ?? null)}</TableCell>
                    <TableCell className={NUM}>{formatNumber(r.sigma_period ?? null)}</TableCell>
                    <TableCell className={NUM}>{formatNumber(sigmaDaily, 4)}</TableCell>
                    <TableCell className={NUM}>
                      {r.lead_time_days_used != null ? `${formatNumber(r.lead_time_days_used)} hari` : "—"}
                    </TableCell>
                    <TableCell className={NUM}>
                      {formatNumber(r.z_value ?? null, 4)}
                      {r.service_level_pct_used != null && (
                        <span className="block text-xs text-muted-foreground">
                          {formatPercent(r.service_level_pct_used)}
                        </span>
                      )}
                    </TableCell>
                    <TableCell className={`${NUM} font-medium`}>
                      {formatQty(r.safety_stock, unit(id))}
                      {manual && <span className="block text-xs text-muted-foreground">SS manual (master material)</span>}
                      {r.adjustment_source && (
                        <span className="block text-xs text-muted-foreground">
                          disesuaikan kapasitas · sistem {formatNumber(r.safety_stock_system ?? null)}
                        </span>
                      )}
                    </TableCell>
                    <TableCell className={NUM}>
                      {r.waste_factor != null ? (
                        formatNumber(r.waste_factor, 4)
                      ) : (
                        <span className="text-xs text-muted-foreground">belum ada data pemakaian aktual</span>
                      )}
                    </TableCell>
                    <TableCell className={`${NUM} font-medium`}>{formatQty(r.buffer_stock ?? "0", unit(id))}</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </ScrollTable>
        </TabsContent>

        {/* 3. Total kebutuhan material */}
        <TabsContent value="total" className="flex flex-col gap-2">
          <Formula>Total kebutuhan material = Σ MRP horizon + safety stock + buffer stock — dasar perhitungan EOQ (tab 4).</Formula>
          <ScrollTable>
            <TableHeader>
              <TableRow>
                <TableHead>Material</TableHead>
                <TableHead className={NUM}>Σ MRP ({periods.length} periode)</TableHead>
                <TableHead className={NUM}>Safety stock</TableHead>
                <TableHead className={NUM}>Buffer stock</TableHead>
                <TableHead className={NUM}>Total kebutuhan</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {materialIds.map((id) => {
                const r = recById.get(id);
                const mrp = mrpTotal(id);
                const ss = num(r?.safety_stock) ?? 0;
                const b = num(r?.buffer_stock) ?? 0;
                return (
                  <TableRow key={id}>
                    <TableCell className="whitespace-nowrap">{label(id)}</TableCell>
                    <TableCell className={NUM}>{formatNumber(mrp)}</TableCell>
                    <TableCell className={NUM}>{formatNumber(ss)}</TableCell>
                    <TableCell className={NUM}>{formatNumber(b)}</TableCell>
                    <TableCell className={`${NUM} font-medium`}>{formatQty(mrp + ss + b, unit(id))}</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </ScrollTable>
        </TabsContent>

        {/* 4. EOQ & kebijakan inventory */}
        <TabsContent value="eoq" className="flex flex-col gap-2">
          <Formula>
            Dasar EOQ = total kebutuhan (MRP + safety stock + buffer stock; SS + B dibagi rata ke tiap periode).
            EOQ klasik = √(2·A·S ÷ (i·C)), A = rata-rata total kebutuhan per periode × 12. EOQ dinamis = Σ total
            kebutuhan ÷ n, n = jumlah pesanan dengan total biaya (n·S + Σ stok akhir·H) terkecil. EOQ dipakai = EOQ
            hitung dibulatkan ke atas ke kelipatan MOQ.
          </Formula>
          <PolicySummary recommendations={recommendations} />
          <ScrollTable>
            <TableHeader>
              <TableRow>
                <TableHead>Material</TableHead>
                <TableHead>Metode</TableHead>
                <TableHead className={NUM}>Kebutuhan tahunan (A, dari total kebutuhan)</TableHead>
                <TableHead className={NUM}>Biaya pesan (S)</TableHead>
                <TableHead className={NUM}>Biaya simpan</TableHead>
                <TableHead className={NUM}>EOQ hitung</TableHead>
                <TableHead className={NUM}>MOQ</TableHead>
                <TableHead className={NUM}>EOQ dipakai</TableHead>
                <TableHead>Kebijakan qty pesan</TableHead>
                <TableHead className={NUM}>Biaya pesan / thn</TableHead>
                <TableHead className={NUM}>Biaya simpan / thn</TableHead>
                <TableHead className={NUM}>TIC</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {materialIds.map((id) => {
                const r = recById.get(id);
                if (!r) return null;
                const classic = r.eoq_method === "classic";
                return (
                  <TableRow key={id}>
                    <TableCell className="whitespace-nowrap">{label(id)}</TableCell>
                    <TableCell>
                      {classic ? "Klasik" : r.eoq_method === "dynamic" ? "Dinamis" : "—"}
                      {ITEM_STATUS_NOTE[r.item_status ?? ""] && (
                        <span className="block text-xs text-muted-foreground">{ITEM_STATUS_NOTE[r.item_status ?? ""]}</span>
                      )}
                    </TableCell>
                    <TableCell className={NUM}>{formatNumber(r.annual_demand ?? null)}</TableCell>
                    <TableCell className={NUM}>{formatMoney(r.ordering_cost_per_order ?? null)}</TableCell>
                    <TableCell className={NUM}>
                      {classic
                        ? `i ${formatPercent(r.holding_rate_used ?? null)} × C ${formatMoney(r.unit_price_used ?? null, 2)}`
                        : `H ${formatMoney(r.holding_cost_per_unit ?? null, 2)} /unit/periode`}
                    </TableCell>
                    <TableCell className={NUM}>{formatNumber(r.eoq_raw_qty ?? null)}</TableCell>
                    <TableCell className={NUM}>{formatNumber(r.moq_used ?? null)}</TableCell>
                    <TableCell className={`${NUM} font-medium`}>{formatQty(r.eoq_qty ?? null, unit(id))}</TableCell>
                    <TableCell className="whitespace-nowrap">
                      {QTY_POLICY_LABEL[r.order_qty_policy_used ?? ""] ?? "—"}
                      {r.order_qty_policy_used === "order_up_to" && (
                        <span className="block text-xs text-muted-foreground">
                          S = {formatNumber(r.order_up_to_level ?? null)}
                        </span>
                      )}
                    </TableCell>
                    <TableCell className={NUM}>{formatMoney(r.ordering_cost ?? null)}</TableCell>
                    <TableCell className={NUM}>{formatMoney(r.holding_cost ?? null)}</TableCell>
                    <TableCell className={`${NUM} font-medium`}>{formatMoney(r.total_inventory_cost ?? null)}</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </ScrollTable>
        </TabsContent>

        {/* 5. ROP */}
        <TabsContent value="rop" className="flex flex-col gap-2">
          <Formula>
            ROP = μ harian × L + SS{ropFormulas.has("with_buffer") ? " (+ buffer stock bila rumus with_buffer)" : ""}, μ
            harian = μ per periode ÷ hari per periode. Pesan bila stok sebelum pesan ≤ ROP; pesanan diasumsikan tiba
            di periode yang sama (batasan thesis).
          </Formula>
          <ScrollTable>
            <TableHeader>
              <TableRow>
                <TableHead>Material</TableHead>
                <TableHead className={NUM}>μ harian</TableHead>
                <TableHead className={NUM}>Lead time (L)</TableHead>
                <TableHead className={NUM}>μ × L</TableHead>
                <TableHead className={NUM}>Safety stock</TableHead>
                <TableHead className={NUM}>Buffer stock</TableHead>
                <TableHead>Rumus</TableHead>
                <TableHead className={NUM}>ROP</TableHead>
                <TableHead className={NUM}>Stok saat ini</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Jadwal pesan / kedatangan</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {materialIds.map((id) => {
                const r = recById.get(id);
                if (!r) return null;
                const mu = num(r.mu_period);
                const days = num(r.period_days);
                const lead = num(r.lead_time_days_used);
                const muDaily = mu !== null && days ? mu / days : null;
                const demandLt = muDaily !== null && lead !== null ? muDaily * lead : null;
                const withBuffer = r.rop_formula_used === "with_buffer";
                const arrivals = periods.filter((p) => (rowsByMaterial.get(id)?.get(p)?.order_qty ?? 0) > 0);
                return (
                  <TableRow key={id}>
                    <TableCell className="whitespace-nowrap">{label(id)}</TableCell>
                    <TableCell className={NUM}>{formatNumber(muDaily, 4)}</TableCell>
                    <TableCell className={NUM}>{lead !== null ? `${formatNumber(lead)} hari` : "—"}</TableCell>
                    <TableCell className={NUM}>{formatNumber(demandLt)}</TableCell>
                    <TableCell className={NUM}>{formatNumber(r.safety_stock)}</TableCell>
                    <TableCell className={NUM}>{withBuffer ? formatNumber(r.buffer_stock ?? "0") : "—"}</TableCell>
                    <TableCell className="whitespace-nowrap">{ROP_FORMULA_LABEL[r.rop_formula_used ?? ""] ?? "—"}</TableCell>
                    <TableCell className={`${NUM} font-medium`}>{formatQty(r.reorder_point, unit(id))}</TableCell>
                    <TableCell className={NUM}>
                      {formatNumber(r.current_stock_used ?? null)}
                      {r.stock_source && (
                        <span className="block text-xs text-muted-foreground">
                          {r.stock_source === "snapshot" ? "stok ERP" : "input manual"}
                        </span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant={STATUS_VARIANT[r.status]}>{STATUS_LABEL[r.status]}</Badge>
                    </TableCell>
                    <TableCell>
                      {arrivals.length ? (
                        <ul className="flex flex-col gap-0.5 text-xs">
                          {arrivals.map((p) => (
                            <li key={p} className="whitespace-nowrap">
                              {formatDate(p)} · {formatQty(rowsByMaterial.get(id)?.get(p)?.order_qty ?? 0, unit(id))}
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <span className="text-xs text-muted-foreground">tidak ada pesanan di horizon</span>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </ScrollTable>
        </TabsContent>

        {/* 6. Kapasitas & utilisasi gudang per grup material */}
        <TabsContent value="capacity" className="flex flex-col gap-4">
          <Formula>
            Per grup material per periode: stok akhir = stok awal + kedatangan − pemakaian. Kedatangan = jadwal dari
            ROP (tahap 5), qty = kebijakan qty pesan (tahap 4). Utilisasi = Σ stok grup ÷ kapasitas grup × 100%.
          </Formula>
          {policies.has("order_up_to") && (
            <Alert variant="warning">
              <AlertDescription>
                Kebijakan qty pesan yang dipakai adalah order-up-to, bukan kelipatan EOQ. Agar qty pembelian = hasil EOQ,
                ubah &quot;Kebijakan qty pesan&quot; di Pengaturan Forecast lalu jalankan ulang perencanaan.
              </AlertDescription>
            </Alert>
          )}
          <CapacityByGroup
            periods={periods}
            rowsByMaterial={rowsByMaterial}
            materialById={materialById}
            label={label}
          />
        </TabsContent>

        {/* 7. Simulasi stok (in/out, tanpa utilisasi) */}
        <TabsContent value="simulation" className="flex flex-col gap-2">
          <Formula>Stok akhir = stok awal + masuk (kedatangan hasil ROP) − keluar (pemakaian MRP).</Formula>
          <StockProjectionTable rows={projection} materials={materials} simulation />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function Formula({ children }: { children: React.ReactNode }) {
  return <p className="text-sm text-muted-foreground">{children}</p>;
}

function ScrollTable({ children }: { children: React.ReactNode }) {
  return (
    <div className="overflow-x-auto rounded-lg border">
      <Table>{children}</Table>
    </div>
  );
}

function PolicySummary({ recommendations }: { recommendations: ReorderRecommendation[] }) {
  const first = recommendations[0];
  if (!first) return null;
  return (
    <dl className="grid gap-2 text-sm sm:grid-cols-4">
      <div className="rounded-md border p-2">
        <dt className="text-xs text-muted-foreground">Target service level</dt>
        <dd className="tabular-nums">{formatPercent(first.service_level_pct_used ?? null)}</dd>
      </div>
      <div className="rounded-md border p-2">
        <dt className="text-xs text-muted-foreground">Rumus ROP</dt>
        <dd>{ROP_FORMULA_LABEL[first.rop_formula_used ?? ""] ?? "—"}</dd>
      </div>
      <div className="rounded-md border p-2">
        <dt className="text-xs text-muted-foreground">Kebijakan qty pesan</dt>
        <dd>{QTY_POLICY_LABEL[first.order_qty_policy_used ?? ""] ?? "—"}</dd>
      </div>
      <div className="rounded-md border p-2">
        <dt className="text-xs text-muted-foreground">Biaya pesan per pesanan (S)</dt>
        <dd className="tabular-nums">{formatMoney(first.ordering_cost_per_order ?? null)}</dd>
      </div>
    </dl>
  );
}

function CapacityByGroup({
  periods,
  rowsByMaterial,
  materialById,
  label,
}: {
  periods: string[];
  rowsByMaterial: Map<string, Map<string, StockProjectionRow>>;
  materialById: Map<string, Material>;
  label: (id: string) => string;
}) {
  const groups = new Map<string, { name: string; members: string[] }>();
  const ungrouped: string[] = [];
  for (const id of rowsByMaterial.keys()) {
    const category = materialById.get(id)?.category;
    const key = materialGroupKey(category);
    if (!key) {
      ungrouped.push(id);
      continue;
    }
    const g = groups.get(key) ?? { name: (category ?? "").trim(), members: [] };
    g.members.push(id);
    groups.set(key, g);
  }

  return (
    <>
      {[...groups.entries()]
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([key, g]) => {
          const uom = materialById.get(g.members[0])?.unit;
          return (
            <section key={key} aria-label={`Grup ${g.name}`} className="flex flex-col gap-2">
              <p className="text-sm font-medium">
                Grup {g.name}
                <span className="font-normal text-muted-foreground">
                  {" "}
                  · {g.members.map((id) => materialById.get(id)?.code ?? id).join(", ")}
                </span>
              </p>
              <ScrollTable>
                <TableHeader>
                  <TableRow>
                    <TableHead>Periode</TableHead>
                    <TableHead className={NUM}>Stok awal</TableHead>
                    <TableHead className={NUM}>Kedatangan (ROP × qty pesan)</TableHead>
                    <TableHead className={NUM}>Pemakaian</TableHead>
                    <TableHead className={NUM}>Stok akhir</TableHead>
                    <TableHead className={NUM}>Kapasitas</TableHead>
                    <TableHead>Utilisasi awal</TableHead>
                    <TableHead>Utilisasi akhir</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {periods.map((p) => {
                    const rows = g.members
                      .map((id) => rowsByMaterial.get(id)?.get(p))
                      .filter((r): r is StockProjectionRow => Boolean(r));
                    const sum = (f: (r: StockProjectionRow) => number) => rows.reduce((s, r) => s + f(r), 0);
                    // Utilisasi & flag dihitung backend per grup — sama untuk semua anggota.
                    const ref = rows[0];
                    return (
                      <TableRow key={p}>
                        <TableCell>{formatDate(p)}</TableCell>
                        <TableCell className={NUM}>{formatNumber(sum((r) => r.opening_qty))}</TableCell>
                        <TableCell className={NUM}>{formatNumber(sum((r) => r.order_qty))}</TableCell>
                        <TableCell className={NUM}>{formatNumber(sum((r) => r.usage_qty))}</TableCell>
                        <TableCell className={NUM}>{formatNumber(sum((r) => r.ending_qty))}</TableCell>
                        <TableCell className={NUM}>{formatQty(ref?.capacity_qty ?? null, uom)}</TableCell>
                        <TableCell>
                          <Utilization pct={ref?.utilization_opening_pct ?? null} />
                        </TableCell>
                        <TableCell>
                          <span className="flex flex-wrap items-center gap-2">
                            <Utilization pct={ref?.utilization_ending_pct ?? null} />
                            {ref?.is_within_capacity === false && (
                              <Badge variant="destructive">Melebihi kapasitas</Badge>
                            )}
                          </span>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </ScrollTable>
            </section>
          );
        })}
      {groups.size === 0 && <p className="text-sm text-muted-foreground">Belum ada material yang punya grup.</p>}
      {ungrouped.length > 0 && (
        <p className="text-sm text-muted-foreground">
          Tanpa grup material (utilisasi tidak dihitung): {ungrouped.map(label).join(", ")}. Atur grup di master
          Material dan kapasitasnya di menu Gudang.
        </p>
      )}
    </>
  );
}
