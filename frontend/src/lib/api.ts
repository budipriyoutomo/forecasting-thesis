import type { ApiResponse, HealthData } from "@/types/api";
import type { LoginResponseData, User } from "@/types/auth";
import type { Material, MaterialInput } from "@/types/material";
import type { UploadResponseData, UploadSessionSummary } from "@/types/upload";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Semua response backend mengikuti envelope { success, data|error } (AGENTS.md §4),
// jadi setiap fungsi di sini mengembalikan ApiResponse<T>, bukan data mentah —
// error bisnis diteruskan apa adanya, tidak dilempar sebagai exception.
async function request<T>(path: string, init?: RequestInit): Promise<ApiResponse<T>> {
  const res = await fetch(`${BASE_URL}${path}`, init);
  return (await res.json()) as ApiResponse<T>;
}

const jsonHeaders = { "Content-Type": "application/json" };

// Contoh pola API client — perluas per endpoint di docs/ARCHITECTURE.md §5.
export const api = {
  health: (): Promise<ApiResponse<HealthData>> => request<HealthData>("/health", { cache: "no-store" }),

  auth: {
    login: (email: string, password: string): Promise<ApiResponse<LoginResponseData>> =>
      request<LoginResponseData>("/api/v1/auth/login", {
        method: "POST",
        headers: jsonHeaders,
        body: JSON.stringify({ email, password }),
      }),

    me: (token: string): Promise<ApiResponse<User>> =>
      request<User>("/api/v1/auth/me", {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      }),
  },

  materials: {
    list: (token: string): Promise<ApiResponse<Material[]>> =>
      request<Material[]>("/api/v1/materials", {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      }),

    create: (input: MaterialInput, token: string): Promise<ApiResponse<Material>> =>
      request<Material>("/api/v1/materials", {
        method: "POST",
        headers: { ...jsonHeaders, Authorization: `Bearer ${token}` },
        body: JSON.stringify(input),
      }),

    update: (id: string, input: Partial<MaterialInput>, token: string): Promise<ApiResponse<Material>> =>
      request<Material>(`/api/v1/materials/${id}`, {
        method: "PUT",
        headers: { ...jsonHeaders, Authorization: `Bearer ${token}` },
        body: JSON.stringify(input),
      }),

    remove: (id: string, token: string): Promise<ApiResponse<{ id: string; deleted: boolean }>> =>
      request<{ id: string; deleted: boolean }>(`/api/v1/materials/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      }),
  },

  uploads: {
    create: (file: File, token: string): Promise<ApiResponse<UploadResponseData>> => {
      const form = new FormData();
      form.append("file", file);

      return request<UploadResponseData>("/api/v1/uploads", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      });
    },

    list: (token: string): Promise<ApiResponse<UploadSessionSummary[]>> =>
      request<UploadSessionSummary[]>("/api/v1/uploads", {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      }),
  },
};
