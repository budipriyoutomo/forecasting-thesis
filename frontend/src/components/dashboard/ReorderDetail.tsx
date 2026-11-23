"use client";

import { Badge } from "@/components/ui/badge";
import { formatDateTime, formatMoney, formatNumber, formatPercent, formatQty } from "@/lib/format";
import type { ReorderRecommendation } from "@/types/reorder";

export const ROP_FORMULA_LABEL: Record<string, string> = {
  standard: "μ·L + SS",
  with_buffer: "μ·L + SS + B",
};

export const ITEM_STATUS_NOTE: Record<string, string> = {
  MISSING_UNIT_PRICE: "Harga material belum diisi — EOQ dinamis",
  MISSING_HOLDING_RATE: "i (%) template biaya belum diisi — EOQ dinamis",
};

const ADJUST_LABEL: Record<string, string> = { suggested: "usulan sistem", custom: "kustom planner" };

function Item({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5 rounded-md border p-2">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="text-sm tabular-nums">{children}</dd>
    </div>
  );
}

// CR v3.6 §6 — rincian lengkap satu rekomendasi reorder. SEMUA field ReorderRecommendation
// (types/reorder.ts) punya tempat di sini — dicek per field oleh ReorderTable.test.
export function ReorderDetail({ rec, unit }: { rec: ReorderRecommendation; unit?: string }) {
  const q = (v: string | null | undefined) => formatQty(v ?? null, unit);
  const adjusted = Boolean(rec.adjustment_source);
  return (
    <div className="flex flex-col gap-4">
      <section className="flex flex-col gap-2">
        <h3 className="text-sm font-medium">Kebijakan stok</h3>
        <dl className="grid gap-2 sm:grid-cols-2">
          <Item label="Safety stock">
            {q(rec.safety_stock)}
            {adjusted && (
              <span className="block text-xs text-muted-foreground">
                sistem <s>{q(rec.safety_stock_system)}</s> · disesuaikan kapasitas (
                {ADJUST_LABEL[rec.adjustment_source as string]})
              </span>
            )}
          </Item>
          <Item label="Buffer stock">
            {q(rec.buffer_stock ?? "0")}
            {rec.buffer_stock_system != null && (
              <span className="block text-xs text-muted-foreground">
                sistem <s>{q(rec.buffer_stock_system)}</s>
              </span>
            )}
          </Item>
          <Item label="Faktor waste">
            {rec.waste_factor != null ? `${formatNumber(rec.waste_factor, 4)} (${((Number(rec.waste_factor) - 1) * 100).toFixed(1)}%)` : "—"}
          </Item>
          <Item label="Service level efektif">{formatPercent(rec.service_level_effective ?? null, 1)}</Item>
          <Item label="Reorder point">
            {q(rec.reorder_point)}
            {rec.rop_formula_used && (
              <span className="block text-xs text-muted-foreground">{ROP_FORMULA_LABEL[rec.rop_formula_used]}</span>
            )}
          </Item>
          <Item label="Status">{rec.status}</Item>
        </dl>
      </section>

      <section className="flex flex-col gap-2">
        <h3 className="text-sm font-medium">Kuantitas pesan</h3>
        <dl className="grid gap-2 sm:grid-cols-2">
          <Item label="Qty pesan (sistem)">{q(rec.recommended_order_qty)}</Item>
          <Item label="Kebijakan qty">
            {rec.order_qty_policy_used === "eoq"
              ? "Kelipatan EOQ"
              : rec.order_qty_policy_used === "order_up_to"
                ? "Order-up-to"
                : "—"}
          </Item>
          <Item label="Order-up-to (S)">{q(rec.order_up_to_level)}</Item>
          <Item label="MOQ dipakai">{q(rec.moq_used)}</Item>
          <Item label="EOQ">
            {q(rec.eoq_qty)}
            {rec.eoq_method && (
              <span className="block text-xs text-muted-foreground">
                {rec.eoq_method === "classic" ? "Klasik √(2AS/iC)" : "Dinamis"}
              </span>
            )}
          </Item>
          <Item label="Annual demand">{q(rec.annual_demand)}</Item>
        </dl>
      </section>

      <section className="flex flex-col gap-2">
        <h3 className="text-sm font-medium">Biaya</h3>
        <dl className="grid gap-2 sm:grid-cols-2">
          <Item label="Biaya pesan / tahun">{formatMoney(rec.ordering_cost ?? null)}</Item>
          <Item label="Biaya simpan / tahun">{formatMoney(rec.holding_cost ?? null)}</Item>
          <Item label="Total biaya persediaan (TIC)">{formatMoney(rec.total_inventory_cost ?? null)}</Item>
          <Item label="Harga material (C)">{formatMoney(rec.unit_price_used ?? null, 2)}</Item>
          <Item label="Holding rate (i)">{formatPercent(rec.holding_rate_used ?? null)}</Item>
          <Item label="Status data">
            {ITEM_STATUS_NOTE[rec.item_status ?? ""] ?? (rec.item_status === "COMPLETED" ? "Lengkap" : "—")}
          </Item>
        </dl>
      </section>

      <section className="flex flex-col gap-2">
        <h3 className="text-sm font-medium">Input perhitungan</h3>
        <dl className="grid gap-2 sm:grid-cols-2">
          <Item label="μ kebutuhan / periode">{q(rec.mu_period)}</Item>
          <Item label="σ kebutuhan / periode">{q(rec.sigma_period)}</Item>
          <Item label="Hari per periode">{rec.period_days != null ? `${formatNumber(rec.period_days)} hari` : "—"}</Item>
          <Item label="Lead time (L)">
            {rec.lead_time_days_used != null ? `${formatNumber(rec.lead_time_days_used)} hari` : "—"}
          </Item>
          <Item label="Faktor Z">{formatNumber(rec.z_value ?? null, 4)}</Item>
          <Item label="Target service level">{formatPercent(rec.service_level_pct_used ?? null)}</Item>
          <Item label="EOQ hitung (sebelum MOQ)">{q(rec.eoq_raw_qty)}</Item>
          <Item label="Biaya pesan per pesanan (S)">{formatMoney(rec.ordering_cost_per_order ?? null)}</Item>
          <Item label="Biaya simpan per unit (H)">{formatMoney(rec.holding_cost_per_unit ?? null, 2)}</Item>
        </dl>
      </section>

      <section className="flex flex-col gap-2">
        <h3 className="text-sm font-medium">Stok & override</h3>
        <dl className="grid gap-2 sm:grid-cols-2">
          <Item label="Stok dipakai">
            {q(rec.current_stock_used)}
            {rec.stock_source && (
              <span className="block text-xs text-muted-foreground">
                {rec.stock_source === "snapshot" ? "Stok ERP" : "Input manual"}
              </span>
            )}
          </Item>
          <Item label="Override planner">
            {rec.override_qty != null ? (
              <>
                {q(rec.override_qty)} <Badge variant="warning">Override</Badge>
                <span className="block text-xs text-muted-foreground">
                  {rec.override_reason ?? "—"} · {formatDateTime(rec.override_at ?? null)}
                </span>
              </>
            ) : (
              "Belum di-override"
            )}
          </Item>
        </dl>
      </section>
    </div>
  );
}
