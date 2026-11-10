// Cocok dengan backend/app/schemas/product.py
export interface Product {
  id: string;
  code: string;
  name: string;
  category: string | null;
  unit: string;
  // Satu-satunya harga produk (label UI "Harga produk"), Rupiah (Decimal → string).
  // HPP (cost_price) dihapus 10 Nov 2026.
  selling_price?: string | null;
}

export interface ProductInput {
  code: string;
  name: string;
  category?: string | null;
  unit: string;
  selling_price?: number | null;
}
