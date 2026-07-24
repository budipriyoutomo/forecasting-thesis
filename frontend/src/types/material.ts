// Cocok dengan backend/app/schemas/material.py
export interface Material {
  id: string;
  code: string;
  name: string;
  category: string | null;
  unit: string;
  lead_time_days: number;
  moq: string; // Decimal diserialisasi sebagai string oleh backend
  manual_safety_stock: string | null;
}

export interface MaterialInput {
  code: string;
  name: string;
  category?: string | null;
  unit: string;
  lead_time_days: number;
  moq: number;
  manual_safety_stock?: number | null;
}
