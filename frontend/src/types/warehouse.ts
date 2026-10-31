// Cocok dengan backend/app/schemas/warehouse.py — kapasitas per produk.
// Fase 10 (2 Oktober 2026): input pallet/dus/kombinasi; `capacity_dus`,
// `capacity_qty` (unit produk) & `uom` (= unit produk) adalah turunan server.
export type CapacityMode = "PALLET" | "DUS" | "COMBINED";

export type WarehouseTarget = "product" | "material";

export interface WarehouseConfig {
  id: string;
  // Fase 11.6: target polimorfik — produk (gudang FG) atau material (gudang packaging).
  item_type?: WarehouseTarget;
  product_id: string | null;
  material_id?: string | null;
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
  item_type?: WarehouseTarget; // absen = product (kontrak lama)
  product_id?: string;
  material_id?: string;
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
