// Cocok dengan backend/app/schemas/bom.py
export interface Bom {
  id: string;
  product_id: string;
  material_id: string;
  qty_per_unit: string; // Decimal diserialisasi sebagai string oleh backend
}

export interface BomInput {
  product_id: string;
  material_id: string;
  qty_per_unit: number;
}
