// Cocok dengan backend/app/schemas/warehouse.py — kapasitas per produk.
// Fase 10 (2 Oktober 2026): input pallet/dus/kombinasi; `capacity_dus`,
// `capacity_qty` (unit produk) & `uom` (= unit produk) adalah turunan server.
export type CapacityMode = "PALLET" | "DUS" | "COMBINED";

export interface WarehouseConfig {
  id: string;
  product_id: string;
  capacity_mode: CapacityMode;
  pallet_qty: string; // Decimal → string
  dus_qty: string;
  dus_per_pallet: string | null;
  pcs_per_dus: string | null;
  capacity_dus: string;
  capacity_qty: string;
  uom: string;
}

export interface WarehouseCapacityInput {
  capacity_mode: CapacityMode;
  pallet_qty: number;
  dus_qty: number;
  dus_per_pallet: number | null;
  pcs_per_dus: number | null;
}

export interface WarehouseConfigInput extends WarehouseCapacityInput {
  product_id: string;
}

export interface WarehouseProductValidation {
  product_id: string;
  required_qty: string;
  capacity_qty: string;
  is_within_capacity: boolean;
}

export interface WarehouseValidation {
  run_id: string;
  is_within_capacity: boolean;
  details: WarehouseProductValidation[];
}
