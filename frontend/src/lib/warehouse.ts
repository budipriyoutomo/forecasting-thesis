import type { CapacityMode, WarehouseCapacityInput } from "@/types/warehouse";

// Cermin backend/app/services/warehouse_service.py (compute_effective_capacity) —
// dipakai untuk pratinjau di form saja; angka resmi tetap dihitung server.
const DUS_LIKE_UNITS = new Set(["DUS", "KARTON", "BOX", "CTN"]);

export const CAPACITY_MODE_LABELS: Record<CapacityMode, string> = {
  PALLET: "Pallet",
  DUS: "Dus",
  COMBINED: "Kombinasi",
};

export function isDusLike(unit: string): boolean {
  return DUS_LIKE_UNITS.has(unit.trim().toUpperCase());
}

export const usesPallet = (mode: CapacityMode) => mode === "PALLET" || mode === "COMBINED";
export const usesDus = (mode: CapacityMode) => mode === "DUS" || mode === "COMBINED";

/** Kapasitas efektif {dus, qty (unit produk)}, atau null bila input belum lengkap. */
export function computeEffectiveCapacity(
  input: WarehouseCapacityInput,
  productUnit: string,
): { dus: number; qty: number } | null {
  let dus = 0;
  if (usesPallet(input.capacity_mode)) {
    if (!input.dus_per_pallet || input.dus_per_pallet <= 0) return null;
    dus += input.pallet_qty * input.dus_per_pallet;
  }
  if (usesDus(input.capacity_mode)) dus += input.dus_qty;

  if (isDusLike(productUnit)) return { dus, qty: dus };
  if (!input.pcs_per_dus || input.pcs_per_dus <= 0) return null;
  return { dus, qty: dus * input.pcs_per_dus };
}

export interface MaterialGroupOption {
  /** Nama grup seperti pertama kali ditemukan (dirapikan). */
  name: string;
  /** Kunci pencocokan tanpa beda besar/kecil huruf — sama dengan backend. */
  key: string;
  /** Unit bersama anggota grup; null bila unit anggota berbeda-beda. */
  unit: string | null;
  codes: string[];
}

export const materialGroupKey = (v: string | null | undefined) => (v ?? "").trim().toLowerCase();

// Grup material = `materials.category` (19 Nov 2026), dipakai kapasitas gudang per grup.
export function materialGroups(
  materials: { code: string; unit: string; category?: string | null }[],
): MaterialGroupOption[] {
  const groups = new Map<string, MaterialGroupOption>();
  for (const m of materials) {
    const key = materialGroupKey(m.category);
    if (!key) continue;
    const g = groups.get(key) ?? { name: (m.category ?? "").trim(), key, unit: m.unit, codes: [] };
    if (g.unit !== null && g.unit.trim().toUpperCase() !== m.unit.trim().toUpperCase()) g.unit = null;
    g.codes.push(m.code);
    groups.set(key, g);
  }
  return [...groups.values()]
    .map((g) => ({ ...g, codes: [...g.codes].sort() }))
    .sort((a, b) => a.name.localeCompare(b.name));
}
