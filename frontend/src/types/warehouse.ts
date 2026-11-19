// Cocok dengan backend/app/schemas/warehouse.py — kapasitas per produk.
// Fase 10 (2 Oktober 2026): input pallet/dus/kombinasi; `capacity_dus`,
// `capacity_qty` (unit produk) & `uom` (= unit produk) adalah turunan server.
export type CapacityMode = "PALLET" | "DUS" | "COMBINED";

// 19 Nov 2026: gudang material dikonfigurasi per GRUP material (materials.category),
// menggantikan per item material (Fase 11.6).
export type WarehouseTarget = "product" | "material_group";

export interface WarehouseConfig {
  id: string;
  // Target polimorfik — produk (gudang FG) atau grup material (gudang packaging).
  item_type?: WarehouseTarget;
  product_id: string | null;
  material_id?: string | null; // legacy, tidak diisi lagi
  material_group?: string | null;
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
  material_group?: string;
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
