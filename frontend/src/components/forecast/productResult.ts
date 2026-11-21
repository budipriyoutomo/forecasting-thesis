// Helper murni hasil per produk (CR v3.6 §5) — dipakai tabel ringkasan & Sheet detail.
import type { ForecastResult } from "@/types/forecast";
import type { Product } from "@/types/product";

export function productLabel(r: ForecastResult, product?: Product): string {
  return product ? `${product.code} — ${product.name}` : r.product_id;
}

/** Sumber metode berlaku — tanpa pernah mengaku "dipilih otomatis" (Fase 11.15). */
export function sourceLabel(r: ForecastResult): string | null {
  if (r.status !== "COMPLETED" || r.selection_status === "PENDING_SELECTION") return null;
  if (r.selection_mode === "manual") return "dipilih manual sebelum run";
  if (r.selection_reason) return "dipilih planner";
  return "hasil run lama"; // pemenang otomatis sebelum Fase 11.15
}

/** Total & rata-rata per periode deret forecast yang berlaku (CR v3.6 §7.3). */
export function forecastTotals(r: ForecastResult): { total: number; average: number; periods: number } | null {
  if (!r.forecast?.length) return null;
  const total = r.forecast.reduce((sum, p) => sum + p.value, 0);
  return { total, average: total / r.forecast.length, periods: r.forecast.length };
}

/** Metrik metode berlaku; untuk hasil belum dipilih null. */
export function appliedMetric(r: ForecastResult, key: "mad" | "mfe" | "mape"): number | null {
  return r.method_used ? r[key] : null;
}

export const FAILURE_FIX: Record<string, string> = {
  INSUFFICIENT_DATA:
    "Lengkapi histori demand produk ini (upload CSV demand dengan periode lebih panjang), lalu buat forecast baru.",
  MODEL_SELECTION_FAILED:
    "Periksa data demand produk ini (banyak nilai nol / lonjakan ekstrem), aktifkan metode lain di menu Pengaturan, lalu buat forecast baru.",
};
