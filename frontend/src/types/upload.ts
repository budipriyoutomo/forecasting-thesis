// Cocok dengan backend/app/schemas/upload.py — UploadResponseData
export interface UploadResponseData {
  session_id: string;
  n_rows: number;
  n_materials_detected: number;
  preview: Record<string, unknown>[];
  warnings: string[];
  status: "pending" | "validated";
}

// Envelope response ada di types/api.ts — di-re-export supaya import lama tetap jalan.
export type { ApiSuccess, ApiError, ApiResponse } from "./api";
