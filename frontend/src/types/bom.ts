// Cocok dengan backend/app/schemas/bom.py
export interface Bom {
  id: string;
  product_id: string;
  material_id: string;
  qty_per_unit: string; // Decimal diserialisasi sebagai string oleh backend
  // Fase 10 — read-only: qty_per_unit × harga material (null bila material tanpa harga)
  line_cost?: string | null;
  // 19 Nov 2026 — baris `boms` selalu level 1; level 2+ dari MaterialComponent
  level?: number;
}

// BOM level 2+ (material induk → komponen), GET /material-components
export interface MaterialComponent {
  id: string;
  parent_material_id: string;
  component_material_id: string;
  qty_per_unit: number;
}

// POST /boms/bulk — satu produk, banyak material sekaligus
export interface BomBulkInput {
  product_id: string;
  items: { material_id: string; qty_per_unit: number }[];
}

export interface BomInput {
  product_id: string;
  material_id: string;
  qty_per_unit: number;
}
