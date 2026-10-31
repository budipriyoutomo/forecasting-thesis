import type { ApiResponse, HealthData } from "@/types/api";
import type { LoginResponseData, User } from "@/types/auth";
import type { DashboardSummary } from "@/types/dashboard";
import type { ForecastRunInput, ForecastRunResponse } from "@/types/forecast";
import type { Bom, BomInput } from "@/types/bom";
import type { Material, MaterialInput } from "@/types/material";
import type { CostSummary, InventoryMetric } from "@/types/metrics";
import type {
  CostTemplate,
  CostTemplateInput,
  CostTemplateSummary,
} from "@/types/costTemplate";
import type { BomTreeNode } from "@/components/boms/BomTree";
import type { ExternalVariable, ExternalVariableInput, ImportResult } from "@/types/externalVariable";
import type { LatestStock, MaterialReceipt, MaterialReceiptInput, WasteFactor } from "@/types/inventory";
import type { PlanningSummary, StockProjectionRow } from "@/types/planning";
import type { ForecastSettings, ForecastSettingsInput } from "@/types/forecastSettings";
import type { Override, OverrideInput } from "@/types/override";
import type { Product, ProductInput } from "@/types/product";
import type {
  WarehouseConfig,
  WarehouseCapacityInput,
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

// Upload file (CSV/Excel) multipart — dipakai seluruh endpoint `/import` (Fase 11.2b+).
function uploadFile<T>(path: string, file: File, token: string): Promise<ApiResponse<T>> {
  const form = new FormData();
  form.append("file", file);
  return request<T>(path, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: form });
}

function authed(token: string, init: RequestInit = {}): RequestInit {
  const json = init.body && typeof init.body === "string" ? jsonHeaders : {};
  return { cache: "no-store", ...init, headers: { ...json, Authorization: `Bearer ${token}` } };
}

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

  // Fase 11.1/11.5 — stok ERP, kedatangan, pemakaian aktual
  inventory: {
    latest: (token: string) => request<LatestStock[]>("/api/v1/stock-snapshots/latest", authed(token)),
    importSnapshots: (file: File, token: string) =>
      uploadFile<ImportResult>("/api/v1/stock-snapshots/import", file, token),
    receipts: (token: string) => request<MaterialReceipt[]>("/api/v1/material-receipts", authed(token)),
    createReceipt: (input: MaterialReceiptInput, token: string) =>
      request<MaterialReceipt>(
        "/api/v1/material-receipts",
        authed(token, { method: "POST", body: JSON.stringify(input) }),
      ),
    removeReceipt: (id: string, token: string) =>
      request<{ id: string; deleted: boolean }>(`/api/v1/material-receipts/${id}`, authed(token, { method: "DELETE" })),
    importReceipts: (file: File, token: string) =>
      uploadFile<ImportResult>("/api/v1/material-receipts/import", file, token),
    wasteFactors: (token: string) => request<WasteFactor[]>("/api/v1/material-usage/waste-factors", authed(token)),
    importUsage: (file: File, token: string) => uploadFile<ImportResult>("/api/v1/material-usage/import", file, token),
  },

  // Fase 11.3 — BOM multi-level
  bomTree: {
    get: (productId: string, token: string) =>
      request<BomTreeNode>(`/api/v1/boms/tree?product_id=${encodeURIComponent(productId)}`, authed(token)),
    addComponent: (parentId: string, componentId: string, qty: number, token: string) =>
      request<{ id: string }>(
        `/api/v1/materials/${parentId}/components`,
        authed(token, { method: "POST", body: JSON.stringify({ component_material_id: componentId, qty_per_unit: qty }) }),
      ),
    removeComponent: (id: string, token: string) =>
      request<{ id: string; deleted: boolean }>(`/api/v1/material-components/${id}`, authed(token, { method: "DELETE" })),
  },

  // Fase 11.6/11.8 — pipeline tahap 2→4 & proyeksi stok
  planning: {
    run: (runId: string, currentStock: Record<string, number> | null, token: string) =>
      request<PlanningSummary>(
        `/api/v1/forecast/runs/${runId}/plan`,
        authed(token, { method: "POST", body: JSON.stringify({ current_stock: currentStock }) }),
      ),
    projection: (runId: string, token: string) =>
      request<StockProjectionRow[]>(`/api/v1/forecast/runs/${runId}/stock-projection`, authed(token)),
  },

  externalVariables: {
    list: (token: string) => request<ExternalVariable[]>("/api/v1/external-variables", authed(token)),
    create: (input: ExternalVariableInput, token: string) =>
      request<ExternalVariable>(
        "/api/v1/external-variables",
        authed(token, { method: "POST", body: JSON.stringify(input) }),
      ),
    update: (id: string, input: ExternalVariableInput, token: string) =>
      request<ExternalVariable>(
        `/api/v1/external-variables/${id}`,
        authed(token, { method: "PUT", body: JSON.stringify(input) }),
      ),
    remove: (id: string, token: string) =>
      request<{ id: string; deleted: boolean }>(`/api/v1/external-variables/${id}`, authed(token, { method: "DELETE" })),
    clearValues: (id: string, token: string) =>
      request<{ id: string; deleted_values: number }>(
        `/api/v1/external-variables/${id}/values`,
        authed(token, { method: "DELETE" }),
      ),
    importValues: (file: File, token: string) =>
      uploadFile<ImportResult>("/api/v1/external-variables/values/import", file, token),
  },

  forecastSettings: {
    get: (token: string): Promise<ApiResponse<ForecastSettings>> =>
      request<ForecastSettings>("/api/v1/forecast-settings", {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      }),

    update: (input: ForecastSettingsInput, token: string): Promise<ApiResponse<ForecastSettings>> =>
      request<ForecastSettings>("/api/v1/forecast-settings", {
        method: "PUT",
        headers: { ...jsonHeaders, Authorization: `Bearer ${token}` },
        body: JSON.stringify(input),
      }),
  },

  costTemplates: {
    list: (token: string): Promise<ApiResponse<CostTemplate[]>> =>
      request<CostTemplate[]>("/api/v1/cost-templates", {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      }),

    summary: (id: string, token: string): Promise<ApiResponse<CostTemplateSummary>> =>
      request<CostTemplateSummary>(`/api/v1/cost-templates/${id}/summary`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      }),

    create: (input: CostTemplateInput, token: string): Promise<ApiResponse<CostTemplate>> =>
      request<CostTemplate>("/api/v1/cost-templates", {
        method: "POST",
        headers: { ...jsonHeaders, Authorization: `Bearer ${token}` },
        body: JSON.stringify(input),
      }),

    update: (id: string, input: CostTemplateInput, token: string): Promise<ApiResponse<CostTemplate>> =>
      request<CostTemplate>(`/api/v1/cost-templates/${id}`, {
        method: "PUT",
        headers: { ...jsonHeaders, Authorization: `Bearer ${token}` },
        body: JSON.stringify(input),
      }),

    activate: (id: string, token: string): Promise<ApiResponse<CostTemplate>> =>
      request<CostTemplate>(`/api/v1/cost-templates/${id}/activate`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      }),

    remove: (id: string, token: string): Promise<ApiResponse<{ id: string; deleted: boolean }>> =>
      request<{ id: string; deleted: boolean }>(`/api/v1/cost-templates/${id}`, {
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
      input: WarehouseCapacityInput,
      token: string,
    ): Promise<ApiResponse<WarehouseConfig>> =>
      request<WarehouseConfig>(`/api/v1/warehouse/config/${id}`, {
        method: "PUT",
        headers: { ...jsonHeaders, Authorization: `Bearer ${token}` },
        body: JSON.stringify(input),
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
