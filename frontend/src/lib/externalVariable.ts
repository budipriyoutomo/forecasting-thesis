import type {
  ExternalScope,
  ExternalValueType,
  ExternalVariableValueChange,
  ImportResult,
} from "@/types/externalVariable";

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

// ── Ubah nilai per periode dari dialog "Ubah" (21 Nov 2026) — PUT /external-variables/{id}/values ──

export interface EditableValueRow {
  /** "YYYY-MM-DD" (baris tersimpan) atau "YYYY-MM" (input bulan baris baru) */
  period: string;
  product_id: string | null;
  /** Teks input; koma desimal diterima */
  value: string;
  /** Nilai tersimpan sebagai teks; null = baris baru */
  original: string | null;
}

/** Normalisasi "YYYY-MM[-DD]" → "YYYY-MM-01" (sama dengan backend: periode = awal bulan). */
function monthStart(period: string): string | null {
  const m = /^(\d{4})-(\d{2})/.exec(period);
  return m ? `${m[1]}-${m[2]}-01` : null;
}

/** Baris editor → item yang berubah/baru + daftar error (semua dikumpulkan, tidak berhenti di yang pertama). */
export function valueChanges(
  rows: EditableValueRow[],
  variable: { value_type: ExternalValueType; scope: ExternalScope },
): { items: ExternalVariableValueChange[]; errors: string[] } {
  const items: ExternalVariableValueChange[] = [];
  const errors: string[] = [];
  rows.forEach((row) => {
    const text = row.value.trim();
    if (row.original === null && !text && !row.period) return; // baris baru kosong
    if (row.original !== null && text === row.original) return; // tidak berubah
    const label = row.period ? row.period.slice(0, 7) : "baris baru";
    const period = monthStart(row.period);
    if (!period) {
      errors.push(`${label}: Periode wajib diisi.`);
      return;
    }
    if (variable.scope === "product" && !row.product_id) {
      errors.push(`${label}: Produk wajib untuk variabel per produk.`);
      return;
    }
    const value = Number(text.replace(/\s/g, "").replace(",", "."));
    if (!text || !Number.isFinite(value)) {
      errors.push(`${label}: nilai bukan angka valid.`);
      return;
    }
    if (variable.value_type === "flag" && value !== 0 && value !== 1) {
      errors.push(`${label}: variabel flag harus bernilai 0 atau 1.`);
      return;
    }
    items.push({ period, value, product_id: variable.scope === "product" ? row.product_id : null });
  });
  return { items, errors };
}
