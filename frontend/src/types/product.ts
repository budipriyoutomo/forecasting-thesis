// Cocok dengan backend/app/schemas/product.py
export interface Product {
  id: string;
  code: string;
  name: string;
  category: string | null;
  unit: string;
  cost_price?: string | null; // HPP per unit, Rupiah (Decimal → string)
  selling_price?: string | null; // harga jual per unit, Rupiah
}

export interface ProductInput {
  code: string;
  name: string;
  category?: string | null;
  unit: string;
  cost_price?: number | null;
  selling_price?: number | null;
}
