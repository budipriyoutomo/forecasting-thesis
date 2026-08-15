// Formatter terpusat. Sebelumnya tiap komponen punya helper sendiri (dan sebagian
// tabel mencetak Decimal mentah seperti "22400.0000"), jadi tampilan angka tidak
// seragam antar halaman.
//
// Backend menyerialisasi Decimal sebagai string (AGENTS.md §4), maka semua fungsi
// di sini menerima string maupun number supaya pemanggil tidak perlu mengonversi.

const EMPTY = "—";

export type Numeric = string | number | null | undefined;

/** null/undefined/"" → null. Selain itu number, atau null bila tidak terurai. */
function toNumber(value: Numeric): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

export function formatNumber(value: Numeric, maximumFractionDigits = 2): string {
  const n = toNumber(value);
  if (n === null) return EMPTY;
  return n.toLocaleString("id-ID", { maximumFractionDigits });
}

export function formatPercent(value: Numeric, maximumFractionDigits = 2): string {
  const n = toNumber(value);
  if (n === null) return EMPTY;
  return `${n.toLocaleString("id-ID", { maximumFractionDigits })}%`;
}

export function formatMoney(value: Numeric): string {
  const n = toNumber(value);
  if (n === null) return EMPTY;
  // Rupiah tidak lazim ditulis sampai sen untuk angka sebesar biaya persediaan.
  return `Rp ${n.toLocaleString("id-ID", { maximumFractionDigits: 0 })}`;
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return EMPTY;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return EMPTY;
  return d.toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" });
}
