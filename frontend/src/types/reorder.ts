// Cocok dengan backend/app/schemas/reorder.py
export type ReorderStatus = "urgent" | "safe" | "overstock";

export interface ReorderRecommendation {
  material_id: string;
  safety_stock: string; // Decimal sebagai string
  reorder_point: string;
  recommended_order_qty: string;
  status: ReorderStatus;
}
