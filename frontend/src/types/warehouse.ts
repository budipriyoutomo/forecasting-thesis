// Cocok dengan backend/app/schemas/warehouse.py — kapasitas per produk, angka bebas.
// `uom` free input teks (mis. "Dus", "Pcs", "Karton") — tanpa tabel master UOM.
export interface WarehouseConfig {
  id: string;
  product_id: string;
  capacity_qty: string; // Decimal → string
  uom: string;
}

export interface WarehouseConfigInput {
  product_id: string;
  capacity_qty: number;
  uom: string;
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
