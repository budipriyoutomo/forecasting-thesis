import type { ApiResponse, HealthData } from "@/types/api";
import type { LoginResponseData, User } from "@/types/auth";
import type { DashboardSummary } from "@/types/dashboard";
import type { ForecastRunInput, ForecastRunResponse } from "@/types/forecast";
import type { Bom, BomInput } from "@/types/bom";
import type { Material, MaterialInput } from "@/types/material";
import type { CostSummary, InventoryMetric } from "@/types/metrics";
import type { Override, OverrideInput } from "@/types/override";
import type { Product, ProductInput } from "@/types/product";
import type {
  WarehouseConfig,
  WarehouseConfigInput,
  WarehouseValidation,
} from "@/types/warehouse";
import type { ReorderRecommendation } from "@/types/reorder";
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

  products: {
    list: (token: string): Promise<ApiResponse<Product[]>> =>
      request<Product[]>("/api/v1/products", {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      }),

    create: (input: ProductInput, token: string): Promise<ApiResponse<Product>> =>
      request<Product>("/api/v1/products", {
        method: "POST",
        headers: { ...jsonHeaders, Authorization: `Bearer ${token}` },
        body: JSON.stringify(input),
      }),

    update: (id: string, input: Partial<ProductInput>, token: string): Promise<ApiResponse<Product>> =>
      request<Product>(`/api/v1/products/${id}`, {
        method: "PUT",
        headers: { ...jsonHeaders, Authorization: `Bearer ${token}` },
        body: JSON.stringify(input),
      }),

    remove: (id: string, token: string): Promise<ApiResponse<{ id: string; deleted: boolean }>> =>
      request<{ id: string; deleted: boolean }>(`/api/v1/products/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      }),
  },

  boms: {
    list: (productId: string | null, token: string): Promise<ApiResponse<Bom[]>> => {
      const qs = productId ? `?product_id=${encodeURIComponent(productId)}` : "";
      return request<Bom[]>(`/api/v1/boms${qs}`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      });
    },

    create: (input: BomInput, token: string): Promise<ApiResponse<Bom>> =>
      request<Bom>("/api/v1/boms", {
        method: "POST",
        headers: { ...jsonHeaders, Authorization: `Bearer ${token}` },
        body: JSON.stringify(input),
      }),

    update: (id: string, input: Partial<BomInput>, token: string): Promise<ApiResponse<Bom>> =>
      request<Bom>(`/api/v1/boms/${id}`, {
        method: "PUT",
        headers: { ...jsonHeaders, Authorization: `Bearer ${token}` },
        body: JSON.stringify(input),
      }),

    remove: (id: string, token: string): Promise<ApiResponse<{ id: string; deleted: boolean }>> =>
      request<{ id: string; deleted: boolean }>(`/api/v1/boms/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
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

  warehouse: {
    list: (token: string): Promise<ApiResponse<WarehouseConfig[]>> =>
      request<WarehouseConfig[]>("/api/v1/warehouse/config", {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      }),

    create: (input: WarehouseConfigInput, token: string): Promise<ApiResponse<WarehouseConfig>> =>
      request<WarehouseConfig>("/api/v1/warehouse/config", {
        method: "POST",
        headers: { ...jsonHeaders, Authorization: `Bearer ${token}` },
        body: JSON.stringify(input),
      }),

    update: (
      id: string,
      capacityQty: number,
      token: string,
    ): Promise<ApiResponse<WarehouseConfig>> =>
      request<WarehouseConfig>(`/api/v1/warehouse/config/${id}`, {
        method: "PUT",
        headers: { ...jsonHeaders, Authorization: `Bearer ${token}` },
        body: JSON.stringify({ capacity_qty: capacityQty }),
      }),

    remove: (id: string, token: string): Promise<ApiResponse<{ id: string; deleted: boolean }>> =>
      request<{ id: string; deleted: boolean }>(`/api/v1/warehouse/config/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      }),

    validateRun: (runId: string, token: string): Promise<ApiResponse<WarehouseValidation>> =>
      request<WarehouseValidation>(`/api/v1/forecast/runs/${runId}/warehouse-validation`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      }),
  },

  dashboard: {
    summary: (token: string): Promise<ApiResponse<DashboardSummary>> =>
      request<DashboardSummary>("/api/v1/dashboard/summary", {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      }),
  },

  metrics: {
    // Fase 7 — biaya & evaluasi kinerja inventory per run (docs/ARCHITECTURE.md §5).
    costSummary: (runId: string, token: string): Promise<ApiResponse<CostSummary>> =>
      request<CostSummary>(`/api/v1/forecast/runs/${runId}/cost-summary`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      }),

    inventory: (runId: string, token: string): Promise<ApiResponse<InventoryMetric[]>> =>
      request<InventoryMetric[]>(`/api/v1/forecast/runs/${runId}/inventory-metrics`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      }),
  },

  forecast: {
    methods: (token: string): Promise<ApiResponse<{ methods: string[] }>> =>
      request<{ methods: string[] }>("/api/v1/forecast/methods", {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      }),

    createRun: (input: ForecastRunInput, token: string): Promise<ApiResponse<ForecastRunResponse>> =>
      request<ForecastRunResponse>("/api/v1/forecast/runs", {
        method: "POST",
        headers: { ...jsonHeaders, Authorization: `Bearer ${token}` },
        body: JSON.stringify(input),
      }),

    getRun: (runId: string, token: string): Promise<ApiResponse<ForecastRunResponse>> =>
      request<ForecastRunResponse>(`/api/v1/forecast/runs/${runId}`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      }),
  },

  reorder: {
    generate: (
      runId: string,
      currentStock: Record<string, number>,
      token: string,
    ): Promise<ApiResponse<ReorderRecommendation[]>> =>
      request<ReorderRecommendation[]>("/api/v1/reorder/recommendations", {
        method: "POST",
        headers: { ...jsonHeaders, Authorization: `Bearer ${token}` },
        body: JSON.stringify({ run_id: runId, current_stock: currentStock }),
      }),

    list: (
      runId: string,
      status: string | null,
      token: string,
    ): Promise<ApiResponse<ReorderRecommendation[]>> => {
      const qs = new URLSearchParams({ run_id: runId });
      if (status) qs.set("status", status);
      return request<ReorderRecommendation[]>(`/api/v1/reorder/recommendations?${qs.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      });
    },
  },

  overrides: {
    create: (input: OverrideInput, token: string): Promise<ApiResponse<Override>> =>
      request<Override>("/api/v1/overrides", {
        method: "POST",
        headers: { ...jsonHeaders, Authorization: `Bearer ${token}` },
        body: JSON.stringify(input),
      }),

    list: (targetId: string, token: string): Promise<ApiResponse<Override[]>> =>
      request<Override[]>(`/api/v1/overrides?target_id=${encodeURIComponent(targetId)}`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
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
