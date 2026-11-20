import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DashboardPage from "@/app/(dashboard)/dashboard/page";
import { api } from "@/lib/api";
import type { DashboardSummary } from "@/types/dashboard";

vi.mock("@/lib/auth", () => ({ getToken: () => "tok" }));

const FULL: DashboardSummary = {
  n_materials: 37,
  latest_run: {
    run_id: "run-1", status: "COMPLETED", n_products: 9, n_completed: 8, n_failed: 1,
    avg_mase: 0.82, avg_mape: 12.5, avg_mad: 4.25, avg_mfe: -1.2, total_inventory_cost: 1500000,
    created_at: "2026-11-20T08:00:00Z", created_by: "Planner A", n_pending_selection: 3,
    total_inventory_cost_baseline: 2000000, savings_pct: 25,
  },
  reorder_status_counts: { urgent: 4, safe: 11, overstock: 2 },
  n_recent_overrides: 5,
  warehouse: {
    is_within_capacity: false, n_products_over: 6, n_products_checked: 9,
    products_over: Array.from({ length: 6 }, (_, i) => ({ product_id: `p${i}`, code: `SKU-${i}`, name: `Produk ${i}`, excess_qty: 100 - i })),
  },
  inventory_metrics: {
    baseline: { service_level: 0.9, fill_rate: 0.93, stock_out_rate: 0.1, inventory_turnover: 4 },
    forecastiq: { service_level: 0.975, fill_rate: 0.991, stock_out_rate: 0.025, inventory_turnover: 5.5 },
  },
  attention: { n_failed_products: 1, n_missing_cost_data: 7, n_shortage_periods: 13 },
};

function renderWith(summary: DashboardSummary) {
  vi.spyOn(api.dashboard, "summary").mockResolvedValue({ success: true, data: summary } as never);
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <DashboardPage />
    </QueryClientProvider>,
  );
}

describe("Dashboard (CR v3.6 §3)", () => {
  beforeEach(() => vi.restoreAllMocks());

  // Satu harapan per field DashboardSummary — bila field baru ditambah, tambahkan di sini.
  const FIELDS: [string, () => void][] = [
    ["n_materials", () => expect(screen.getAllByText(/37 material/).length).toBeGreaterThan(0)],
    // 21 Nov 2026 — tile akurasi: metrik MAD/|MFE|/MAPE rata-rata terkecil + namanya
    ["latest_run.avg_mfe (terkecil) + nama metrik", () => {
      expect(screen.getByText("Akurasi forecast (MFE rata-rata)")).toBeDefined();
      expect(screen.getByText("-1.20")).toBeDefined();
    }],
    ["latest_run.avg_mad & avg_mape di hint", () =>
      expect(screen.getByText(/error rata-rata terkecil · MAD 4\.25 · MAPE 12\.50%/)).toBeDefined()],
    ["latest_run.avg_mase tidak tampil", () => {
      expect(screen.queryByText(/MASE/)).toBeNull();
      expect(screen.queryByText("0,82")).toBeNull();
    }],
    ["latest_run.total_inventory_cost", () => expect(screen.getByText(/Rp\s?1\.500\.000/)).toBeDefined()],
    ["latest_run.savings_pct & baseline", () => expect(screen.getByText(/hemat 25% vs baseline Rp\s?2\.000\.000/)).toBeDefined()],
    ["latest_run.created_at/by", () => expect(screen.getByText(/oleh Planner A/)).toBeDefined()],
    ["latest_run.status & counts", () => {
      expect(screen.getByText("Selesai")).toBeDefined();
      expect(screen.getByText(/8 berhasil · 1 gagal dari 9 produk/)).toBeDefined();
    }],
    ["latest_run.n_pending_selection CTA", () =>
      expect(screen.getByRole("link", { name: "Pilih metode untuk 3 produk" }).getAttribute("href")).toBe("/forecast/runs/run-1?step=select")],
    ["latest_run.run_id link", () =>
      expect(screen.getByRole("link", { name: /lihat detail run/i }).getAttribute("href")).toBe("/forecast/runs/run-1")],
    ["reorder_status_counts", () => {
      expect(screen.getByText("Segera reorder")).toBeDefined();
      expect(screen.getByText("11")).toBeDefined();
      expect(screen.getByText("Kelebihan stok")).toBeDefined();
    }],
    ["n_recent_overrides", () => expect(screen.getByText(/override planner terbaru/)).toBeDefined()],
    ["warehouse summary", () => expect(screen.getByText(/6 dari 9 produk melebihi kapasitasnya/)).toBeDefined()],
    ["warehouse.products_over (maks 5 + lihat semua)", () => {
      expect(screen.getByText("SKU-0")).toBeDefined();
      expect(screen.queryByText("SKU-5")).toBeNull();
      expect(screen.getByRole("link", { name: /lihat semua \(6\)/i })).toBeDefined();
    }],
    ["inventory_metrics per scope", () => {
      expect(screen.getByText("Existing (baseline)")).toBeDefined();
      expect(screen.getByText("99,1%")).toBeDefined(); // fill rate forecastiq
      expect(screen.getByText("5,5×")).toBeDefined();
    }],
    ["attention", () => {
      expect(screen.getByText(/produk gagal di-forecast/)).toBeDefined();
      expect(screen.getByText(/material tanpa harga/)).toBeDefined();
      expect(screen.getByText(/periode kekurangan stok/)).toBeDefined();
    }],
  ];

  it.each(FIELDS)("field %s punya tempat di UI", async (_name, check) => {
    renderWith(FULL);
    await screen.findByText("Run forecast terakhir");
    check();
  });

  it("tile akurasi memilih MAPE bila rata-ratanya paling kecil (+ label Lewis)", async () => {
    renderWith({ ...FULL, latest_run: { ...FULL.latest_run!, avg_mad: 40, avg_mfe: 30, avg_mape: 12.5 } });
    expect(await screen.findByText("Akurasi forecast (MAPE rata-rata)")).toBeDefined();
    expect(screen.getByText("12.50%")).toBeDefined();
    expect(screen.getByText(/error rata-rata terkecil \(Baik\)/)).toBeDefined();
  });

  it("tidak ada angka reorder ganda (urgent hanya di tile + bar)", async () => {
    renderWith({ ...FULL, reorder_status_counts: { urgent: 4, safe: 11, overstock: 2 } });
    await screen.findByText("Run forecast terakhir");
    expect(screen.queryByText("Perlu reorder")).toBeNull();
    expect(screen.getAllByText("Segera reorder")).toHaveLength(1);
  });

  it("empty state per kartu saat data null", async () => {
    renderWith({
      n_materials: 0, latest_run: null, reorder_status_counts: { urgent: 0, safe: 0, overstock: 0 },
      n_recent_overrides: 0, warehouse: null, inventory_metrics: null, attention: null,
    });
    await screen.findByText("Run forecast terakhir");
    expect(screen.getByText("Belum ada run. Mulai dari menu Forecast.")).toBeDefined();
    expect(screen.getByText("Jalankan perencanaan untuk melihat kinerja inventory.")).toBeDefined();
    expect(screen.getByText(/belum ada rekomendasi reorder/i)).toBeDefined();
    expect(screen.getByText(/tidak ada yang perlu ditindaklanjuti/i)).toBeDefined();
  });
});
