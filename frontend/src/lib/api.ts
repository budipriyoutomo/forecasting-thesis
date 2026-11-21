import type { ApiResponse, HealthData } from "@/types/api";
import type { LoginResponseData, User } from "@/types/auth";
import type { ManagedUser, UserCreateInput, UserUpdateInput } from "@/types/user";
import type { DashboardSummary } from "@/types/dashboard";
import type {
  ForecastResult,
  ForecastRunInput,
  ForecastRunListItem,
  ForecastRunResponse,
  MethodSelectionInput,
  RunSelectionResult,
} from "@/types/forecast";
import type { Bom, BomBulkInput, BomInput, MaterialComponent } from "@/types/bom";
import type { Material, MaterialInput } from "@/types/material";
import type { CostSummary, InventoryMetric } from "@/types/metrics";
import type {
  CostTemplate,
  CostTemplateInput,
  CostTemplateSummary,
} from "@/types/costTemplate";
import type { BomTreeNode } from "@/components/boms/BomTree";
import type {
  ExternalVariable,
  ExternalVariableCoverage,
  ExternalVariableValue,
  ExternalVariableInput,
  ImportDryRunResult,
  ImportResult,
} from "@/types/externalVariable";
import type { LatestStock, MaterialUsageRow, StockSnapshot, WasteFactor } from "@/types/inventory";
import type {
  CapacityAdjustment,
  CapacityAdjustmentInputItem,
  CapacitySuggestion,
  PlanningSummary,
  StockProjectionRow,
} from "@/types/planning";
import type { ForecastSettings, ForecastSettingsInput } from "@/types/forecastSettings";
import type { Override, OverrideInput } from "@/types/override";
import type { Product, ProductDemandCoverage, ProductInput } from "@/types/product";
import type {
  WarehouseConfig,
  WarehouseCapacityInput,
  WarehouseConfigInput,
  WarehouseValidation,
} from "@/types/warehouse";
import type { ReorderRecommendation } from "@/types/reorder";
import type { UploadResponseData, UploadSessionSummary } from "@/types/upload";
import { handleSessionExpired } from "@/lib/session";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Semua response backend mengikuti envelope { success, data|error } (AGENTS.md §4),
// jadi setiap fungsi di sini mengembalikan ApiResponse<T>, bukan data mentah —
// error bisnis diteruskan apa adanya, tidak dilempar sebagai exception.
// Response di luar envelope (network error, 5xx teks polos dari proxy, dsb) dinormalisasi
// jadi ApiError supaya pemanggil selalu aman membaca `res.error.message` (CR v3.5 §1).
async function request<T>(path: string, init?: RequestInit): Promise<ApiResponse<T>> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, init);
  } catch {
    return { success: false, error: { code: "NETWORK_ERROR", message: "Tidak bisa terhubung ke server." } };
  }
  // 401 pada request ber-token = sesi berakhir (CR v3.5 §5.3). Login gagal juga 401 tapi
  // tanpa header Authorization, jadi tidak ikut me-redirect.
  if (res.status === 401 && hasBearer(init)) handleSessionExpired();
  const body: unknown = await res.json().catch(() => null);
  if (body && typeof body === "object" && "success" in body) return body as ApiResponse<T>;
  return {
    success: false,
    error: { code: `HTTP_${res.status}`, message: `Permintaan gagal (status ${res.status}).` },
  };
}

function hasBearer(init?: RequestInit): boolean {
  const auth = new Headers(init?.headers).get("Authorization");
  return Boolean(auth?.startsWith("Bearer "));
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

  // CR v3.7 — User Management (admin, `user.manage`).
  users: {
    list: (token: string): Promise<ApiResponse<ManagedUser[]>> =>
      request<ManagedUser[]>("/api/v1/users", authed(token)),

    create: (input: UserCreateInput, token: string): Promise<ApiResponse<ManagedUser>> =>
      request<ManagedUser>("/api/v1/users", {
        method: "POST",
        headers: { ...jsonHeaders, Authorization: `Bearer ${token}` },
        body: JSON.stringify(input),
      }),

    update: (id: string, input: UserUpdateInput, token: string): Promise<ApiResponse<ManagedUser>> =>
      request<ManagedUser>(`/api/v1/users/${id}`, {
        method: "PUT",
        headers: { ...jsonHeaders, Authorization: `Bearer ${token}` },
        body: JSON.stringify(input),
      }),
  },

  products: {
    list: (token: string): Promise<ApiResponse<Product[]>> =>
      request<Product[]>("/api/v1/products", {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      }),

    // CR v3.6 §5 — jumlah periode histori demand & periode terakhir per produk
    demandCoverage: (token: string): Promise<ApiResponse<ProductDemandCoverage[]>> =>
      request<ProductDemandCoverage[]>("/api/v1/products/demand-coverage", authed(token)),

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

    createBulk: (input: BomBulkInput, token: string): Promise<ApiResponse<Bom[]>> =>
      request<Bom[]>("/api/v1/boms/bulk", {
        method: "POST",
        headers: { ...jsonHeaders, Authorization: `Bearer ${token}` },
        body: JSON.stringify(input),
      }),

    remove: (id: string, token: string): Promise<ApiResponse<{ id: string; deleted: boolean }>> =>
      request<{ id: string; deleted: boolean }>(`/api/v1/boms/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      }),
  },

  // Fase 11.1/11.5 — stok ERP & pemakaian aktual (kedatangan manual dihapus 20 Nov 2026)
  inventory: {
    latest: (token: string) => request<LatestStock[]>("/api/v1/stock-snapshots/latest", authed(token)),
    importSnapshots: (file: File, token: string) =>
      uploadFile<ImportResult>("/api/v1/stock-snapshots/import", file, token),
    snapshots: (materialId: string, token: string) =>
      request<StockSnapshot[]>(`/api/v1/stock-snapshots?material_id=${encodeURIComponent(materialId)}`, authed(token)),
    usage: (materialId: string, token: string) =>
      request<MaterialUsageRow[]>(`/api/v1/material-usage?material_id=${encodeURIComponent(materialId)}`, authed(token)),
    wasteFactors: (token: string) => request<WasteFactor[]>("/api/v1/material-usage/waste-factors", authed(token)),
    importUsage: (file: File, token: string) => uploadFile<ImportResult>("/api/v1/material-usage/import", file, token),
  },

  // Fase 11.3 — BOM multi-level
  bomTree: {
    components: (token: string) => request<MaterialComponent[]>("/api/v1/material-components", authed(token)),
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

  // Fase 11.17 — adjust kapasitas gudang (SS & Buffer) per run
  capacityAdjustments: {
    suggest: (runId: string, token: string) =>
      request<CapacitySuggestion>(
        `/api/v1/forecast/runs/${runId}/capacity-adjustments/suggest`,
        authed(token, { method: "POST" }),
      ),
    list: (runId: string, token: string) =>
      request<{ active: CapacityAdjustment[]; history: CapacityAdjustment[] }>(
        `/api/v1/forecast/runs/${runId}/capacity-adjustments`,
        authed(token),
      ),
    save: (
      runId: string,
      input: { source: "suggested" | "custom"; items: CapacityAdjustmentInputItem[]; reason?: string | null },
      token: string,
    ) =>
      request<CapacityAdjustment[]>(
        `/api/v1/forecast/runs/${runId}/capacity-adjustments`,
        authed(token, { method: "POST", body: JSON.stringify(input) }),
      ),
    reset: (runId: string, reason: string | null, token: string) =>
      request<{ n_reset: number }>(
        `/api/v1/forecast/runs/${runId}/capacity-adjustments/reset`,
        authed(token, { method: "POST", body: JSON.stringify({ reason }) }),
      ),
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
    validateValues: (file: File, token: string) =>
      uploadFile<ImportDryRunResult>("/api/v1/external-variables/values/import?dry_run=true", file, token),
    values: (id: string, token: string) =>
      request<ExternalVariableValue[]>(`/api/v1/external-variables/${encodeURIComponent(id)}/values`, authed(token)),
    coverage: (horizon: number, token: string) =>
      request<ExternalVariableCoverage[]>(`/api/v1/external-variables/coverage?horizon=${horizon}`, authed(token)),
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

    // Nonaktifkan (21 Nov 2026) — tanpa template aktif, EOQ & total biaya memakai biaya default sistem.
    deactivate: (id: string, token: string): Promise<ApiResponse<CostTemplate>> =>
      request<CostTemplate>(`/api/v1/cost-templates/${id}/deactivate`, {
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

    listRuns: (token: string): Promise<ApiResponse<ForecastRunListItem[]>> =>
      request<ForecastRunListItem[]>("/api/v1/forecast/runs", {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      }),

    getRun: (runId: string, token: string): Promise<ApiResponse<ForecastRunResponse>> =>
      request<ForecastRunResponse>(`/api/v1/forecast/runs/${runId}`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      }),

    // Fase 11.15 — planner memilih metode (override append-only, alasan wajib).
    selectMethod: (resultId: string, input: MethodSelectionInput, token: string) =>
      request<ForecastResult>(`/api/v1/forecast/results/${resultId}/selection`, {
        method: "POST",
        headers: { ...jsonHeaders, Authorization: `Bearer ${token}` },
        body: JSON.stringify(input),
      }),

    selectMethodForRun: (runId: string, input: MethodSelectionInput, token: string) =>
      request<RunSelectionResult>(`/api/v1/forecast/runs/${runId}/selection`, {
        method: "POST",
        headers: { ...jsonHeaders, Authorization: `Bearer ${token}` },
        body: JSON.stringify(input),
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

    // Riwayat override reorder per (run, material) — bertahan setelah reorder di-generate ulang.
    listReorder: (runId: string, materialId: string, token: string): Promise<ApiResponse<Override[]>> =>
      request<Override[]>(
        `/api/v1/overrides/reorder?run_id=${encodeURIComponent(runId)}&material_id=${encodeURIComponent(materialId)}`,
        { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" },
      ),
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
