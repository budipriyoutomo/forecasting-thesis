// Cocok dengan backend/app/schemas/product.py
export interface Product {
  id: string;
  code: string;
  name: string;
  category: string | null;
  unit: string;
}

export interface ProductInput {
  code: string;
  name: string;
  category?: string | null;
  unit: string;
}
