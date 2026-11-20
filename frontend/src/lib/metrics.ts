// Sumber tunggal info metrik pengujian peramalan: label, definisi singkat untuk user
// non-teknis, arah "lebih baik", dan interpretasi. Dipakai tabel perbandingan metode,
// tile dashboard, tooltip header, dan tabel ringkasan produk.
//
// Keputusan user 21 Nov 2026: pengujian peramalan HANYA MAD, MFE, MAPE. MSE & MASE tetap
// dihitung & disimpan backend, tetapi tidak ditampilkan.
// Fase 11.15 tetap berlaku: TIDAK ada peringkat/pemenang antar metode.
import { mapeLabel } from "@/lib/mape";
import type { DisplayMetric } from "@/types/forecastSettings";

export type MetricKey = DisplayMetric;

export interface MetricInfo {
  label: string;
  /** Satu-dua kalimat, untuk tooltip header kolom. */
  definition: string;
  /** "lower" = makin kecil makin baik; "zero" = makin dekat 0 makin baik (bias). */
  better: "lower" | "zero";
  /** Interpretasi teks singkat; null bila metrik tidak punya ambang baku. */
  interpret: (value: number | null | undefined) => string | null;
}

export const METRIC_INFO: Record<MetricKey, MetricInfo> = {
  mad: {
    label: "MAD",
    definition: "Mean Absolute Deviation — rata-rata selisih absolut forecast vs aktual, dalam satuan produk.",
    better: "lower",
    interpret: () => null,
  },
  mfe: {
    label: "MFE",
    definition:
      "Mean Forecast Error (bias) — rata-rata selisih bertanda. Positif = forecast cenderung kurang (under), negatif = cenderung lebih (over). Makin dekat 0 makin baik.",
    better: "zero",
    interpret: () => null,
  },
  mape: {
    label: "MAPE",
    definition: "Mean Absolute Percentage Error — rata-rata galat dalam persen dari aktual (skala Lewis).",
    better: "lower",
    interpret: (v) => (v == null ? null : mapeLabel(v)),
  },
};

/** Urutan baku tampilan (sama dengan backend DISPLAY_METRICS). */
export const ALL_METRICS: MetricKey[] = ["mad", "mfe", "mape"];

/** Kolom metrik yang tampil sesuai checkbox Pengaturan Forecast. Nilai lama yang sudah
 * bukan metrik tampil ("mse"/"mase") tersaring; kosong → semua metrik. */
export function metricColumns(displayMetrics: readonly MetricKey[] | undefined): MetricKey[] {
  const chosen = new Set<string>(displayMetrics ?? ALL_METRICS);
  const cols = ALL_METRICS.filter((m) => chosen.has(m));
  return cols.length > 0 ? cols : [...ALL_METRICS];
}

export function formatMetric(value: number | null | undefined, key: MetricKey): string {
  if (value == null || Number.isNaN(value)) return "—";
  return key === "mape" ? `${value.toFixed(2)}%` : value.toFixed(2);
}

/** Tile dashboard (keputusan user 21 Nov 2026): di antara rata-rata MAD, MFE, MAPE run
 * terakhir, tampilkan yang error-nya paling kecil (paling mendekati kebenaran) beserta
 * namanya. MFE dibandingkan dengan nilai absolutnya (bias makin dekat 0 makin baik), tapi
 * nilai yang dikembalikan tetap bertanda. Catatan: satuannya berbeda (unit vs %). */
export function bestAccuracyMetric(avg: Record<MetricKey, number | null | undefined>): {
  key: MetricKey;
  value: number;
} | null {
  let best: { key: MetricKey; value: number } | null = null;
  for (const key of ALL_METRICS) {
    const v = avg[key];
    if (v == null || !Number.isFinite(v)) continue;
    if (best === null || Math.abs(v) < Math.abs(best.value)) best = { key, value: v };
  }
  return best;
}
