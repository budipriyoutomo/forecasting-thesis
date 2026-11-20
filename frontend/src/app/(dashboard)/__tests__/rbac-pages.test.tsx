import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ComponentType } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import BomsPage from "@/app/(dashboard)/boms/page";
import CostTemplatesPage from "@/app/(dashboard)/cost-templates/page";
import ExternalVariablesPage from "@/app/(dashboard)/external-variables/page";
import ForecastSettingsPage from "@/app/(dashboard)/forecast-settings/page";
import ForecastConfigPage from "@/app/(dashboard)/forecast/new/config/page";
import UploadPage from "@/app/(dashboard)/forecast/new/page";
import InventoryPage from "@/app/(dashboard)/inventory/page";
import MaterialsPage from "@/app/(dashboard)/materials/page";
import ProductsPage from "@/app/(dashboard)/products/page";
import WarehousePage from "@/app/(dashboard)/warehouse/page";
import type { Role } from "@/types/auth";

// CR v3.5 §3.6/§3.7 — tombol tulis tidak dirender untuk role tanpa izin; halaman tetap
// bisa dibuka (baca). Hook data di-stub supaya yang diuji hanya gating per role.

const me = vi.hoisted(() => ({ role: "admin" as string, pending: false }));
vi.mock("@/hooks/useAuth", () => ({
  useMe: () => ({ data: me.pending ? undefined : { role: me.role }, isPending: me.pending }),
}));

const stubs = vi.hoisted(() => {
  const mutation = () => ({ mutate: () => {}, reset: () => {}, isPending: false, isError: false, isSuccess: false, error: null, data: undefined });
  const query = (data: unknown) => () => ({ data, isPending: false, isError: false });
  return { mutation, query };
});

const fx = vi.hoisted(() => {
  const PRODUCT = { id: "p1", code: "SKU-1", name: "Teh", category: null, unit: "BTL", selling_price: null };
  const MATERIAL = { id: "m1", code: "BTL", name: "Botol", unit: "PCS", lead_time_days: 7, moq: 0, material_group: "botol" };
  const BOM = { id: "b1", product_id: "p1", material_id: "m1", qty_per_unit: "1", waste_pct: "0" };
  const VARIABLE = { id: "v1", code: "suhu", name: "Suhu", value_type: "numeric", scope: "global", is_active: true, unit: null, description: null };
  const TEMPLATE = { id: "t1", name: "Default", description: null, ordering_cost: "1000", holding_cost: "10", is_active: true, items: [] };
  const WH = { id: "w1", item_type: "material_group", material_group: "botol", product_id: null, capacity_qty: "100" };
  return { PRODUCT, MATERIAL, BOM, VARIABLE, TEMPLATE, WH };
});

vi.mock("@/hooks/useProducts", () => ({
  useProducts: stubs.query([fx.PRODUCT]),
  useCreateProduct: stubs.mutation, useUpdateProduct: stubs.mutation, useDeleteProduct: stubs.mutation,
}));
vi.mock("@/hooks/useMaterials", () => ({
  useMaterials: stubs.query([fx.MATERIAL]),
  useCreateMaterial: stubs.mutation, useUpdateMaterial: stubs.mutation, useDeleteMaterial: stubs.mutation,
}));
vi.mock("@/hooks/useBoms", () => ({
  useBoms: stubs.query([fx.BOM]), useMaterialComponents: stubs.query([]),
  useCreateBomsBulk: stubs.mutation, useUpdateBom: stubs.mutation, useDeleteBom: stubs.mutation,
}));
vi.mock("@/hooks/usePlanning", () => ({
  useBomTree: stubs.query({ material_id: null, code: "SKU-1", name: "Teh", children: [
    { material_id: "m1", code: "BTL", name: "Botol", children: [{ material_id: "m2", component_id: "c1", code: "PRE", name: "Preform", children: [] }] },
  ] }),
  useBomComponent: stubs.mutation,
}));
vi.mock("@/hooks/useWarehouse", () => ({
  useWarehouseConfigs: stubs.query([fx.WH]),
  useCreateWarehouseConfig: stubs.mutation, useUpdateWarehouseConfig: stubs.mutation, useDeleteWarehouseConfig: stubs.mutation,
}));
vi.mock("@/hooks/useCostTemplates", () => ({
  useCostTemplates: stubs.query([fx.TEMPLATE, { ...fx.TEMPLATE, id: "t2", name: "Alt", is_active: false }]),
  useCostTemplateSummary: stubs.query(undefined),
  useCreateCostTemplate: stubs.mutation, useUpdateCostTemplate: stubs.mutation,
  useActivateCostTemplate: stubs.mutation, useDeleteCostTemplate: stubs.mutation,
}));
vi.mock("@/hooks/useExternalVariables", () => ({
  useExternalVariables: stubs.query([fx.VARIABLE]), useExternalVariableCoverage: stubs.query([]),
  useSaveExternalVariable: stubs.mutation, useDeleteExternalVariable: stubs.mutation,
  useImportExternalValues: stubs.mutation, useValidateExternalValues: stubs.mutation,
  useDownloadExternalTemplate: stubs.mutation,
  useExternalVariableValues: stubs.query(undefined),
}));
vi.mock("@/hooks/useForecastSettings", () => ({
  useForecastSettings: stubs.query({
    enabled_methods: ["moving_average"], available_methods: ["moving_average"], display_metrics: ["mape"],
    es_alpha_grid: [0.1, 0.5], es_alpha_metric: "mse", ml_grid_search: false, ma_window: 3, updated_at: null,
  }),
  useUpdateForecastSettings: stubs.mutation,
}));
vi.mock("@/hooks/useInventory", () => ({
  useLatestStock: stubs.query([]), useWasteFactors: stubs.query([]),
  useImportSnapshots: stubs.mutation, useImportUsage: stubs.mutation,
  useStockSnapshots: stubs.query([]), useMaterialUsage: stubs.query([]),
}));

function wrap(Page: ComponentType) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <Page />
    </QueryClientProvider>,
  );
}

function renderAs(role: Role, Page: ComponentType) {
  me.role = role;
  return wrap(Page);
}

const q = (name: RegExp) => screen.queryAllByRole("button", { name });

beforeEach(() => {
  me.pending = false;
});

describe.each([
  ["Produk", ProductsPage, /tambah produk/i],
  ["Material", MaterialsPage, /tambah material/i],
  ["BOM", BomsPage, /tambah bom/i],
  ["Kapasitas gudang", WarehousePage, /tambah kapasitas/i],
  ["Template biaya", CostTemplatesPage, /tambah template/i],
])("Master data %s (master.write = admin)", (_label, Page, addButton) => {
  it("admin melihat tombol tambah, ubah, hapus", () => {
    renderAs("admin", Page);
    expect(q(addButton)).toHaveLength(1);
    expect(q(/^ubah$/i).length).toBeGreaterThan(0);
    expect(q(/^hapus$/i).length).toBeGreaterThan(0);
  });

  it.each(["ppic", "purchasing", "viewer"] as Role[])("%s hanya membaca", (role) => {
    renderAs(role, Page);
    expect(q(addButton)).toHaveLength(0);
    expect(q(/^ubah$/i)).toHaveLength(0);
    expect(q(/^hapus$/i)).toHaveLength(0);
  });
});

describe("BOM multi-level", () => {
  it("komponen level 2 hanya bisa ditambah/dihapus admin", () => {
    renderAs("admin", BomsPage);
    expect(q(/tambah komponen/i).length).toBeGreaterThan(0);
  });

  it("non-admin tidak melihat form komponen", () => {
    renderAs("ppic", BomsPage);
    expect(q(/tambah komponen/i)).toHaveLength(0);
    expect(screen.queryAllByRole("button", { name: /hapus komponen/i })).toHaveLength(0);
  });
});

describe("Template biaya", () => {
  it("tombol aktifkan hanya untuk admin", () => {
    renderAs("admin", CostTemplatesPage);
    expect(q(/aktifkan/i)).toHaveLength(1);
  });
  it("viewer tidak bisa mengaktifkan", () => {
    renderAs("viewer", CostTemplatesPage);
    expect(q(/aktifkan/i)).toHaveLength(0);
  });
});

describe("Variabel eksternal", () => {
  it("admin: definisi + import nilai", () => {
    renderAs("admin", ExternalVariablesPage);
    expect(q(/tambah variabel/i)).toHaveLength(1);
    expect(q(/import nilai/i)).toHaveLength(1);
    expect(q(/validasi file/i)).toHaveLength(1);
    expect(screen.queryAllByRole("switch")).not.toHaveLength(0);
  });

  it("ppic: import nilai (+ dry-run) ya, definisi tidak", () => {
    renderAs("ppic", ExternalVariablesPage);
    expect(q(/import nilai/i)).toHaveLength(1);
    expect(q(/validasi file/i)).toHaveLength(1);
    expect(q(/tambah variabel/i)).toHaveLength(0);
    expect(q(/^ubah$/i)).toHaveLength(0);
    expect(q(/^hapus$/i)).toHaveLength(0);
    expect(screen.queryAllByRole("switch")).toHaveLength(0);
  });

  it.each(["purchasing", "viewer"] as Role[])("%s: hanya baca, tetap boleh unduh template", (role) => {
    renderAs(role, ExternalVariablesPage);
    expect(q(/import nilai/i)).toHaveLength(0);
    expect(q(/validasi file/i)).toHaveLength(0);
    expect(q(/tambah variabel/i)).toHaveLength(0);
    expect(q(/unduh template/i)).toHaveLength(1);
  });
});

describe("Pengaturan forecast (settings.write = admin)", () => {
  it("admin bisa menyimpan", () => {
    renderAs("admin", ForecastSettingsPage);
    expect(q(/simpan/i)).toHaveLength(1);
  });

  it.each(["ppic", "purchasing", "viewer"] as Role[])("%s: form read-only tanpa tombol simpan", (role) => {
    renderAs(role, ForecastSettingsPage);
    expect(q(/simpan/i)).toHaveLength(0);
    for (const box of screen.getAllByRole("checkbox")) expect(box.matches(":disabled")).toBe(true);
  });
});

describe("Persediaan material (data.import_stock = admin, ppic)", () => {
  it.each(["admin", "ppic"] as Role[])("%s bisa import", (role) => {
    renderAs(role, InventoryPage);
    expect(q(/import stok erp/i)).toHaveLength(1);
  });

  it.each(["purchasing", "viewer"] as Role[])("%s hanya melihat", (role) => {
    renderAs(role, InventoryPage);
    expect(q(/import stok erp/i)).toHaveLength(0);
    expect(q(/import pemakaian/i)).toHaveLength(0);
  });
});

describe.each([
  ["Upload demand", UploadPage],
  ["Konfigurasi forecast", ForecastConfigPage],
])("%s (forecast.run = admin, ppic)", (_label, Page) => {
  it.each(["purchasing", "viewer"] as Role[])("%s melihat pesan & link ke halaman baca", (role) => {
    renderAs(role, Page);
    expect(screen.getByText(/hanya ppic\/admin yang dapat menjalankan forecast/i)).toBeDefined();
    expect(screen.getByRole("link", { name: /kedatangan material/i }).getAttribute("href")).toBe("/material-arrivals");
  });

  it("profil belum dimuat → tidak menampilkan pesan terlarang (tidak berkedip)", () => {
    me.pending = true;
    wrap(Page);
    expect(screen.queryByText(/hanya ppic\/admin/i)).toBeNull();
  });
});
