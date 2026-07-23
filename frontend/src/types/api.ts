// Envelope response backend — AGENTS.md §4 / docs/ARCHITECTURE.md §5.
export interface ApiSuccess<T> {
  success: true;
  data: T;
  message?: string;
}

export interface ApiError {
  success: false;
  error: {
    code: string;
    message: string;
  };
}

export type ApiResponse<T> = ApiSuccess<T> | ApiError;

// GET /health — dipakai untuk verifikasi konektivitas frontend → backend (Fase 0).
export interface HealthData {
  status: string;
}
