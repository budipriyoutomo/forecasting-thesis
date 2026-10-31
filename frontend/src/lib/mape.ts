// Interpretasi MAPE (Lewis, 1982 — tabel di docx thesis). Sama dengan backend
// `evaluation.mape_interpretation`.
export function mapeLabel(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return "Tidak terdefinisi";
  if (value < 10) return "Sangat baik";
  if (value < 20) return "Baik";
  if (value < 50) return "Cukup";
  return "Buruk";
}
