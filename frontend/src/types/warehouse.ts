// Cocok dengan backend/app/schemas/warehouse.py
export interface PalletDimension {
  length: number;
  width: number;
  height: number;
}

export interface WarehouseConfig {
  category: string;
  warehouse_area_m2: string; // Decimal → string
  pallet_dimension: PalletDimension;
}

export interface WarehouseConfigInput {
  category?: string;
  warehouse_area_m2: number;
  pallet_dimension: PalletDimension;
}

export interface WarehouseValidation {
  run_id: string;
  total_pallet_capacity: string;
  total_pallet_required: string;
  is_within_capacity: boolean;
}
