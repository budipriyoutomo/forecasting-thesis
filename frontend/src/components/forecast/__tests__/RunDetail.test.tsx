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

function renderDetail(props: Partial<Parameters<typeof RunDetail>[0]> = {}) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <RunDetail runId="run1" {...props} />
    </QueryClientProvider>,
  );
}

const COMPARISON = {
  run_id: "run1", periods: ["2026-12-01"], criteria: ["mad", "mape", "mfe"],
  methods: [{
    method: "moving_average", label: "Moving Average",
    rows: [{ product_id: "p1", status: "OK", forecast: { "2026-12-01": 100 }, total: 100, mad: 1, mape: 8, mfe: 0 }],
    average: { mad: 1, mape: 8, mfe: 0, n: 1, n_total: 1 },
  }],
  run_selection: null,
  product_methods: [],
};

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
  vi.spyOn(api.forecast, "getMethodComparison").mockResolvedValue({ success: true, data: COMPARISON } as never);
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
    expect(within(nav).getByRole("button", { name: /reorder & gudang/i }).textContent).toMatch(/terkunci/i);
    expect(within(nav).getByRole("button", { name: /4\. evaluasi inventory/i }).textContent).toMatch(/terkunci/i);
  });

  it("langkah terkunci menampilkan alasan prasyarat", async () => {
    stub({ run: runOf([RESULT], 0) });
    renderDetail();

    await userEvent.click(await screen.findByRole("button", { name: /5\. reorder & gudang/i }));
    expect(screen.getByText(/jalankan perencanaan dulu/i)).toBeDefined();
  });

  it("sudah ada proyeksi stok → langkah evaluasi inventory (4) setelah perencanaan memuat metrik & biaya", async () => {
    stub({ run: runOf([RESULT], 0), projection: [PROJ_ROW] });
    renderDetail();

    await userEvent.click(await screen.findByRole("button", { name: /4\. evaluasi inventory/i }));
    expect(await screen.findByRole("heading", { name: /4\. evaluasi usulan inventory/i })).toBeDefined();
    expect(api.metrics.inventory).toHaveBeenCalled();
    expect(api.metrics.costSummary).toHaveBeenCalled();
  });

  it("sudah ada proyeksi stok → langkah 5 terbuka default, reorder & kapasitas dimuat otomatis", async () => {
    stub({ run: runOf([RESULT], 0), projection: [PROJ_ROW] });
    renderDetail();

    expect(await screen.findByRole("heading", { name: /5\. reorder & gudang/i })).toBeDefined();
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

  it("navigasi bawah tiap langkah: Kembali ke langkah sebelumnya, Lanjut ke berikutnya", async () => {
    stub({ run: runOf([RESULT], 0), projection: [PROJ_ROW] });
    renderDetail();

    // default langkah 5 (semua selesai) — tidak ada tombol Lanjut, ada Kembali ke langkah 4.
    await screen.findByRole("heading", { name: /5\. reorder & gudang/i });
    expect(screen.queryByRole("button", { name: /^lanjut/i })).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: /kembali: evaluasi inventory/i }));
    expect(await screen.findByRole("heading", { name: /4\. evaluasi usulan inventory/i })).toBeDefined();
    await userEvent.click(screen.getByRole("button", { name: /lanjut: reorder & gudang/i }));
    expect(await screen.findByRole("heading", { name: /5\. reorder & gudang/i })).toBeDefined();
  });

  it("header memuat status run + link ke daftar run", async () => {
    stub({ run: runOf([RESULT], 0) });
    renderDetail();

    const link = await screen.findByRole("link", { name: /daftar run/i });
    expect(link.getAttribute("href")).toBe("/forecast");
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

  // CR v3.7 §4.3 — langkah 1: view per metode (format thesis) default, per produk via toggle.
  it("langkah Forecast: tab default 'Per metode (format thesis)'", async () => {
    stub({ run: runOf([RESULT], 0) });
    renderDetail({ initialStep: "forecast" });

    const tab = await screen.findByRole("tab", { name: /per metode \(format thesis\)/i });
    expect(tab.getAttribute("aria-selected")).toBe("true");
    expect(await screen.findByText(/1\. metode moving average/i)).toBeDefined();
    expect(api.forecast.getMethodComparison).toHaveBeenCalledWith("run1", "tok");
  });

  it("?view=product membuka tabel per produk lama", async () => {
    stub({ run: runOf([RESULT], 0) });
    renderDetail({ initialStep: "forecast", initialView: "product" });

    const tab = await screen.findByRole("tab", { name: /per produk/i });
    expect(tab.getAttribute("aria-selected")).toBe("true");
    expect(await screen.findByText("SKU-1")).toBeDefined();
    expect(screen.queryByText(/1\. metode moving average/i)).toBeNull();
  });

  it("ganti tab → ?view= di URL ikut berubah (step & param lain dipertahankan)", async () => {
    window.history.replaceState(null, "", "/forecast/runs/run1?step=forecast");
    stub({ run: runOf([RESULT], 0) });
    renderDetail({ initialStep: "forecast" });

    await userEvent.click(await screen.findByRole("tab", { name: /per produk/i }));
    expect(window.location.search).toBe("?step=forecast&view=product");
    await userEvent.click(screen.getByRole("tab", { name: /per metode/i }));
    expect(window.location.search).toBe("?step=forecast&view=method");
  });
});
