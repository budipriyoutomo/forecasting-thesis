import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RunDetail } from "@/components/forecast/RunDetail";
import { api } from "@/lib/api";
import type { ForecastResult, ForecastRunResponse } from "@/types/forecast";

vi.mock("@/lib/auth", () => ({ getToken: () => "tok" }));
const me = vi.hoisted(() => ({ role: "ppic" }));
vi.mock("@/hooks/useAuth", () => ({ useMe: () => ({ data: { role: me.role }, isPending: false }) }));

const POINT = [{ date: "2026-12-01", value: 100, lower: 90, upper: 110 }];
const RESULT: ForecastResult = {
  id: "res1", product_id: "p1", status: "COMPLETED", method_used: "moving_average", selection_mode: "auto",
  selection_status: "SELECTED", selection_reason: "stabil", mad: 1, mfe: 0, mse: 1, mape: 8, mase: 0.8,
  candidates_evaluated: [
    { method: "moving_average", mad: 1, mfe: 0, mse: 1, mape: 8, mase: 0.8, forecast: POINT },
    { method: "xgboost", mad: 2, mfe: 0, mse: 2, mape: 9, mase: 1.1, forecast: POINT },
  ],
  explanation: "penjelasan", forecast: POINT, metrics: null, history: [{ date: "2026-11-01", value: 95 }],
};
const PENDING: ForecastResult = {
  ...RESULT, id: "res2", product_id: "p2", method_used: null, selection_status: "PENDING_SELECTION",
  selection_reason: null, forecast: [],
};

function runOf(results: ForecastResult[], nPending: number): ForecastRunResponse {
  return {
    run: { run_id: "run1", status: "COMPLETED", horizon: 12, horizon_unit: "months", n_products: results.length,
      n_completed: results.length, n_failed: 0, n_pending_selection: nPending },
    results,
  };
}

function renderDetail() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <RunDetail runId="run1" />
    </QueryClientProvider>,
  );
}

function stub({ run, projection = [] as unknown[], recs = [] as unknown[] }: { run: ForecastRunResponse; projection?: unknown[]; recs?: unknown[] }) {
  const getRun = vi.spyOn(api.forecast, "getRun").mockResolvedValue({ success: true, data: run } as never);
  vi.spyOn(api.forecast, "listRuns").mockResolvedValue({
    success: true, data: [{ run_id: "run1", status: "COMPLETED", horizon: 12, horizon_unit: "months", created_at: "2026-11-20T08:00:00Z", created_by: "Planner A" }],
  } as never);
  vi.spyOn(api.products, "list").mockResolvedValue({
    success: true, data: [
      { id: "p1", code: "SKU-1", name: "Teh", category: null, unit: "BTL" },
      { id: "p2", code: "SKU-2", name: "Kopi", category: null, unit: "BTL" },
    ],
  } as never);
  vi.spyOn(api.materials, "list").mockResolvedValue({ success: true, data: [] } as never);
  vi.spyOn(api.forecastSettings, "get").mockResolvedValue({
    success: true, data: { display_metrics: ["mad", "mfe", "mape"], service_level_pct: 95 },
  } as never);
  vi.spyOn(api.planning, "projection").mockResolvedValue({ success: true, data: projection } as never);
  vi.spyOn(api.reorder, "list").mockResolvedValue({ success: true, data: recs } as never);
  vi.spyOn(api.metrics, "costSummary").mockResolvedValue({ success: false, error: { code: "X", message: "belum" } } as never);
  vi.spyOn(api.metrics, "inventory").mockResolvedValue({ success: true, data: [] } as never);
  vi.spyOn(api.warehouse, "validateRun").mockResolvedValue({
    success: true, data: { run_id: "run1", is_within_capacity: true, details: [] },
  } as never);
  return { getRun };
}

const PROJ_ROW = {
  material_id: "m1", scenario: "proposed", period: "2026-12-01", opening_qty: 1, receipt_qty: null, usage_qty: 1,
  order_qty: 0, ending_qty: 0, shortage_qty: 0, capacity_qty: null, utilization_opening_pct: null,
  utilization_ending_pct: null, is_within_capacity: null,
};

describe("RunDetail (CR v3.6 §1/§4)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    me.role = "ppic";
  });

  it("render dari useForecastRun(id) — tanpa state mutation (refresh aman)", async () => {
    const { getRun } = stub({ run: runOf([RESULT, PENDING], 1) });
    renderDetail();

    expect(await screen.findByRole("heading", { name: /2\. metode terbaik/i })).toBeDefined();
    expect(getRun).toHaveBeenCalledWith("run1", "tok");
    expect(screen.getByText(/oleh Planner A/)).toBeDefined();
  });

  it("status stepper diturunkan dari data run: pending → langkah 2 perlu tindakan", async () => {
    stub({ run: runOf([RESULT, PENDING], 1) });
    renderDetail();

    const nav = await screen.findByRole("navigation", { name: /langkah run/i });
    const current = within(nav).getByRole("button", { current: "step" });
    expect(current.textContent).toMatch(/metode terbaik.*1 produk menunggu/i);
    expect(within(nav).getByRole("button", { name: /reorder & biaya/i }).textContent).toMatch(/terkunci/i);
  });

  it("langkah terkunci menampilkan alasan prasyarat", async () => {
    stub({ run: runOf([RESULT], 0) });
    renderDetail();

    await userEvent.click(await screen.findByRole("button", { name: /4\. reorder & biaya/i }));
    expect(screen.getByText(/jalankan perencanaan dulu/i)).toBeDefined();
  });

  it("sudah ada proyeksi stok → langkah 4 terbuka default, reorder & kapasitas dimuat otomatis", async () => {
    stub({ run: runOf([RESULT], 0), projection: [PROJ_ROW] });
    renderDetail();

    expect(await screen.findByRole("heading", { name: /4\. reorder & biaya/i })).toBeDefined();
    expect(api.warehouse.validateRun).toHaveBeenCalledWith("run1", "tok");
    expect(screen.queryByRole("button", { name: /cek kapasitas/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /^hitung reorder$/i })).toBeNull();
  });

  it("PPIC: satu tombol Jalankan perencanaan + menu hitung ulang sebagian", async () => {
    stub({ run: runOf([RESULT], 0) });
    renderDetail();

    expect(await screen.findByRole("button", { name: /^jalankan perencanaan$/i })).toBeDefined();
    expect(screen.getByRole("button", { name: /hitung ulang sebagian/i })).toBeDefined();
  });

  it("Viewer: detail run terbaca, tombol aksi disembunyikan", async () => {
    me.role = "viewer";
    stub({ run: runOf([RESULT, PENDING], 1) });
    renderDetail();

    expect(await screen.findByText(/anda melihat dalam mode baca/i)).toBeDefined();
    expect(screen.queryByRole("combobox", { name: /metode untuk semua produk/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /forecast baru/i })).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: /3\. perencanaan/i }));
    expect(screen.queryByRole("button", { name: /jalankan perencanaan/i })).toBeNull();
  });

  it("export dikumpulkan di satu dropdown", async () => {
    stub({ run: runOf([RESULT], 0) });
    renderDetail();

    await userEvent.click(await screen.findByRole("button", { name: /^export$/i }));
    expect(await screen.findByRole("menuitem", { name: /forecast \(excel\)/i })).toBeDefined();
    expect(screen.getByRole("menuitem", { name: /reorder \(pdf\) — jalankan perencanaan dulu/i })).toBeDefined();
  });

  it("run tidak ada → pesan + link kembali", async () => {
    stub({ run: runOf([RESULT], 0) });
    vi.spyOn(api.forecast, "getRun").mockResolvedValue({
      success: false, error: { code: "FORECAST_RUN_NOT_FOUND", message: "Forecast run tidak ditemukan." },
    } as never);
    renderDetail();

    expect(await screen.findByText("Run tidak ditemukan.")).toBeDefined();
    expect(screen.getByRole("link", { name: /kembali ke daftar run/i }).getAttribute("href")).toBe("/forecast");
  });
});
