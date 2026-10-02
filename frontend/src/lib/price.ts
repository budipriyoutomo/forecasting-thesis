import { z } from "zod";

// Field harga opsional di form (Fase 10): string di form supaya kosong ≠ 0,
// dikirim sebagai number | null. Rupiah, tidak boleh negatif.
export const optionalPriceField = z
  .string()
  .refine((v) => v.trim() === "" || Number.isFinite(Number(v)), "Harus berupa angka")
  .refine((v) => v.trim() === "" || Number(v) >= 0, "Tidak boleh negatif");

export const parsePrice = (v: string | undefined): number | null =>
  v === undefined || v.trim() === "" ? null : Number(v);

/** Nilai awal field harga dari Decimal backend ("4500.0000" → "4500"). */
export const priceDefault = (v: string | null | undefined): string =>
  v == null ? "" : String(Number(v));
