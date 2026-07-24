// Cocok dengan backend/app/schemas/upload.py — UploadResponseData
export interface UploadResponseData {
  session_id: string;
  n_rows: number;
  n_materials_detected: number;
  preview: Record<string, unknown>[];
  warnings: string[];
  status: "pending" | "validated";
}

// Ringkasan satu upload di daftar riwayat (GET /uploads) — cocok dengan
// backend/app/schemas/upload.py UploadSessionSummary.
export interface UploadSessionSummary {
  session_id: string;
  file_name: string;
  n_rows: number;
  n_materials_detected: number;
  status: string;
  created_at: string | null;
}

// Envelope response ada di types/api.ts — di-re-export supaya import lama tetap jalan.
export type { ApiSuccess, ApiError, ApiResponse } from "./api";
