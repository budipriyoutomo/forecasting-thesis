import type { ImportResult } from "@/types/externalVariable";

/** Ringkasan import nilai variabel eksternal untuk toast (CR v3.4 §4.1). */
export function importSummary(r: ImportResult): string {
  const parts = [`${r.imported} nilai diimpor`];
  if (r.normalized) parts.push(`${r.normalized} periode digeser ke awal bulan`);
  if (r.overwritten) parts.push(`${r.overwritten} baris ganda (bulan sama) ditimpa baris terakhir`);
  const skipped = skippedSummary(r.skipped);
  if (skipped) parts.push(skipped);
  return parts.join(" · ");
}

/** "3 sel kosong dilewati (suhu 2, inflasi 1)" — null bila tidak ada. */
export function skippedSummary(skipped: Record<string, number> | undefined): string | null {
  const entries = Object.entries(skipped ?? {}).filter(([, n]) => n > 0);
  if (!entries.length) return null;
  const total = entries.reduce((sum, [, n]) => sum + n, 0);
  return `${total} sel kosong dilewati (${entries.map(([code, n]) => `${code} ${n}`).join(", ")})`;
}

// CR v3.4 §4.2 — alasan variabel eksternal di-drop engine ML (`usable_exog`).
const DROP_REASON: Record<string, string> = {
  missing_history: "Nilai histori belum lengkap",
  missing_horizon: "Nilai horizon belum lengkap",
  constant: "Nilai tidak bervariasi di histori",
};
const LEGACY_REASON = "Alasan tidak tercatat (forecast lama)";

export interface ExogUsageInfo {
  used: string[];
  dropped: { code: string; reason: string }[];
  total: number;
}

/** Ringkasan pemakaian variabel eksternal dari `hyperparameters` hasil RF/XGBoost.
 * `exog_dropped` format lama = list kode (tanpa alasan), format baru = {kode: alasan}.
 * null bila metode tidak memakai variabel eksternal. */
export function exogUsage(hp: Record<string, unknown> | null | undefined): ExogUsageInfo | null {
  if (!hp || !("exog_used" in hp || "exog_dropped" in hp)) return null;
  const used = Array.isArray(hp.exog_used) ? hp.exog_used.map(String) : [];
  const raw = hp.exog_dropped;
  const dropped = Array.isArray(raw)
    ? raw.map((code) => ({ code: String(code), reason: LEGACY_REASON }))
    : raw && typeof raw === "object"
      ? Object.entries(raw as Record<string, unknown>).map(([code, reason]) => ({
          code,
          reason: DROP_REASON[String(reason)] ?? String(reason),
        }))
      : [];
  const total = used.length + dropped.length;
  return total === 0 ? null : { used, dropped, total };
}
