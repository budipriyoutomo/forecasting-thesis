// Cocok dengan backend/app/schemas/bom.py
export interface Bom {
  id: string;
  product_id: string;
  material_id: string;
  qty_per_unit: string; // Decimal diserialisasi sebagai string oleh backend
  // Fase 10 — read-only: qty_per_unit × harga material (null bila material tanpa harga)
  line_cost?: string | null;
}

export interface BomInput {
  product_id: string;
  material_id: string;
  qty_per_unit: number;
}
