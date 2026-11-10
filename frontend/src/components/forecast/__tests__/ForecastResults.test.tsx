import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ForecastResults } from "@/components/forecast/ForecastResults";
import type { ForecastCandidate, ForecastResult, ForecastRunResponse } from "@/types/forecast";
import type { Product } from "@/types/product";

const PID = "11111111-1111-1111-1111-111111111111";
const PID2 = "22222222-2222-2222-2222-222222222222";
const POINT = [{ date: "2026-09-01", value: 100, lower: 90, upper: 110 }];

const products: Product[] = [
  { id: PID, code: "SKU-001", name: "Kursi Lipat", category: null, unit: "pcs" },
];

function cand(method: string, mape: number): ForecastCandidate {
  return { method, mad: 1, mfe: -1, mse: 2, mape, mase: null, forecast: POINT, explanation: null };
}

const selected: ForecastResult = {
  id: "r1",
  product_id: PID,
  status: "COMPLETED",
  method_used: "moving_average",
  selection_mode: "auto",
  selection_status: "SELECTED",
  selection_reason: "Paling stabil",
  mad: null,
  mfe: null,
  mse: null,
  mape: 8.2,
  mase: null,
  candidates_evaluated: [cand("moving_average", 8.2), cand("xgboost", 7.1)],
  explanation: null,
  forecast: POINT,
  metrics: null,
};

const pending: ForecastResult = {
  ...selected,
  id: "r2",
  product_id: PID2,
  method_used: null,
  selection_status: "PENDING_SELECTION",
  selection_reason: null,
  mape: null,
  forecast: [],
};

function runOf(results: ForecastResult[], nPending = 0): ForecastRunResponse {
  return {
    run: {
      run_id: "run1",
      status: "COMPLETED",
      horizon: 3,
      horizon_unit: "days",
      n_products: results.length,
      n_completed: results.length,
      n_failed: 0,
      n_pending_selection: nPending,
    },
    results,
  };
}

const data = runOf([selected]);

describe("ForecastResults", () => {
  it("menampilkan kode — nama produk, bukan UUID", () => {
    render(<ForecastResults data={data} products={products} />);

    expect(screen.getByText("SKU-001 — Kursi Lipat")).toBeDefined();
    expect(screen.queryByText(PID)).toBeNull();
  });

  it("jatuh ke product_id saat produk tidak ada di master data", () => {
    render(<ForecastResults data={data} products={[]} />);

    expect(screen.getByText(PID)).toBeDefined();
  });

  it("tetap jalan tanpa prop products", () => {
    render(<ForecastResults data={data} />);

    expect(screen.getByText(PID)).toBeDefined();
  });

  // ── Fase 11.15: tanpa pemenang, planner memilih ──

  it("tidak pernah mengaku 'dipilih otomatis'; pilihan planner + alasannya tampil", () => {
    render(<ForecastResults data={data} />);

    expect(screen.queryByText(/dipilih otomatis/i)).toBeNull();
    expect(screen.getByText(/dipilih planner/i)).toBeDefined();
    expect(screen.getByText(/paling stabil/i)).toBeDefined();
  });

  it("hasil belum dipilih: badge, ringkasan, tabel terbuka, tombol Pilih", async () => {
    const onSelectMethod = vi.fn();
    render(<ForecastResults data={runOf([pending], 1)} onSelectMethod={onSelectMethod} />);

    expect(screen.getAllByText(/metode belum dipilih/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/1 produk menunggu pemilihan metode/i)).toBeDefined();
    await userEvent.click(screen.getByRole("button", { name: /pilih xgboost/i }));

    expect(onSelectMethod).toHaveBeenCalledWith(pending, "xgboost");
  });

  it("hasil yang sudah dipilih tetap bisa diganti metodenya", async () => {
    const onSelectMethod = vi.fn();
    render(<ForecastResults data={data} onSelectMethod={onSelectMethod} />);

    await userEvent.click(screen.getByRole("button", { name: /perbandingan metode/i }));
    await userEvent.click(screen.getByRole("button", { name: /pilih xgboost/i }));

    expect(onSelectMethod).toHaveBeenCalledWith(selected, "xgboost");
  });

  it("pakai satu metode untuk semua produk", async () => {
    const onSelectAll = vi.fn();
    render(<ForecastResults data={runOf([selected, pending], 1)} onSelectAll={onSelectAll} />);

    await userEvent.selectOptions(screen.getByLabelText(/metode untuk semua produk/i), "xgboost");
    await userEvent.click(screen.getByRole("button", { name: /pakai untuk semua produk/i }));

    expect(onSelectAll).toHaveBeenCalledWith("xgboost");
  });

  it("kolom metrik mengikuti displayMetrics", async () => {
    render(<ForecastResults data={runOf([pending], 1)} displayMetrics={["mape"]} onSelectMethod={vi.fn()} />);

    expect(screen.getAllByRole("columnheader").map((h) => h.textContent)).toEqual(["Metode", "MAPE", "Aksi"]);
  });

  it("mode manual: disebut dipilih sebelum run", () => {
    render(
      <ForecastResults
        data={runOf([{ ...selected, selection_mode: "manual", selection_reason: null, candidates_evaluated: [cand("moving_average", 8.2)] }])}
      />,
    );

    expect(screen.getByText(/dipilih manual/i)).toBeDefined();
  });
});
