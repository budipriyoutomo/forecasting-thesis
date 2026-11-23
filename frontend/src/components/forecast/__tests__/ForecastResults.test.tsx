import { render, screen, within } from "@testing-library/react";
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

async function bukaDetail(code: string) {
  await userEvent.click(screen.getByRole("button", { name: `Detail ${code}` }));
}

describe("ForecastResults (CR v3.6 §5 — tabel ringkasan + Sheet)", () => {
  it("menampilkan kode & nama produk, bukan UUID", () => {
    render(<ForecastResults data={data} products={products} />);

    expect(screen.getByText("SKU-001")).toBeDefined();
    expect(screen.getByText("Kursi Lipat")).toBeDefined();
    expect(screen.queryByText(PID)).toBeNull();
  });

  it("jatuh ke product_id saat produk tidak ada di master data", () => {
    render(<ForecastResults data={data} products={[]} />);

    expect(screen.getAllByText(PID).length).toBeGreaterThan(0);
  });

  it("tetap jalan tanpa prop products", () => {
    render(<ForecastResults data={data} />);

    expect(screen.getAllByText(PID).length).toBeGreaterThan(0);
  });

  it("baris ringkasan: metode, MAD/MFE/MAPE (tanpa MSE & MASE), total & rata-rata forecast, sumber", () => {
    render(<ForecastResults data={{ ...data, results: [{ ...selected, mad: 3.5, mfe: -1.25, mase: 0.7 }] }} products={products} />);

    expect(screen.getByText("3.50")).toBeDefined();
    expect(screen.getByText("-1.25")).toBeDefined();
    expect(screen.queryByText("0.70")).toBeNull();
    expect(screen.queryByRole("columnheader", { name: /mase|mse/i })).toBeNull();

    expect(screen.getByText("Moving Average")).toBeDefined();
    expect(screen.getByText("8.20%")).toBeDefined();
    expect(screen.getByText("100 pcs")).toBeDefined(); // total + UoM
    expect(screen.getByText(/dipilih planner/i)).toBeDefined();
  });

  it("filter status & pencarian", async () => {
    render(<ForecastResults data={runOf([selected, pending], 1)} products={products} />);

    expect(screen.getByRole("button", { name: "Belum dipilih (1)" })).toBeDefined();
    await userEvent.click(screen.getByRole("button", { name: "Belum dipilih (1)" }));
    expect(screen.queryByText("SKU-001")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Semua (2)" }));
    await userEvent.type(screen.getByRole("searchbox", { name: /cari kode/i }), "kursi");
    expect(screen.getByText("SKU-001")).toBeDefined();
    expect(screen.queryByText(PID2)).toBeNull();
  });

  // ── Fase 11.15: tanpa pemenang, planner memilih ──

  it("tidak pernah mengaku 'dipilih otomatis'; pilihan planner + alasannya tampil di Sheet", async () => {
    render(<ForecastResults data={data} products={products} />);

    expect(screen.queryByText(/dipilih otomatis/i)).toBeNull();
    await bukaDetail("SKU-001");
    expect(screen.getByText(/paling stabil/i)).toBeDefined();
  });

  it("hasil belum dipilih: badge, ringkasan, tab perbandingan terbuka, tombol Pilih", async () => {
    const onSelectMethod = vi.fn();
    render(<ForecastResults data={runOf([pending], 1)} onSelectMethod={onSelectMethod} />);

    expect(screen.getAllByText(/belum dipilih/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/1 produk menunggu pemilihan metode/i)).toBeDefined();
    await userEvent.click(screen.getByRole("button", { name: `Detail ${PID2}` }));
    await userEvent.click(await screen.findByRole("button", { name: /pilih xgboost/i }));

    expect(onSelectMethod).toHaveBeenCalledWith(pending, "xgboost");
  });

  it("hasil yang sudah dipilih tetap bisa diganti metodenya", async () => {
    const onSelectMethod = vi.fn();
    render(<ForecastResults data={data} products={products} onSelectMethod={onSelectMethod} />);

    await bukaDetail("SKU-001");
    await userEvent.click(screen.getByRole("tab", { name: /perbandingan metode/i }));
    await userEvent.click(await screen.findByRole("button", { name: /pilih xgboost/i }));

    expect(onSelectMethod).toHaveBeenCalledWith(selected, "xgboost");
  });

  it("pakai satu metode untuk semua produk (ui/select)", async () => {
    const onSelectAll = vi.fn();
    render(<ForecastResults data={runOf([selected, pending], 1)} onSelectAll={onSelectAll} />);

    await userEvent.click(screen.getByRole("combobox", { name: /metode untuk semua produk/i }));
    await userEvent.click(await screen.findByRole("option", { name: "XGBoost" }));
    await userEvent.click(screen.getByRole("button", { name: /pakai untuk semua produk/i }));

    expect(onSelectAll).toHaveBeenCalledWith("xgboost");
  });

  it("kolom metrik perbandingan mengikuti displayMetrics", async () => {
    render(<ForecastResults data={runOf([pending], 1)} displayMetrics={["mape"]} onSelectMethod={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: `Detail ${PID2}` }));

    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getAllByRole("columnheader").map((h) => h.textContent)).toEqual([
      "Metode",
      "MAPE",
      "Aksi",
    ]);
  });

  it("mode manual: disebut dipilih sebelum run", () => {
    render(
      <ForecastResults
        data={runOf([{ ...selected, selection_mode: "manual", selection_reason: null, candidates_evaluated: [cand("moving_average", 8.2)] }])}
      />,
    );

    expect(screen.getByText(/dipilih manual/i)).toBeDefined();
  });

  it("metode ML: tab Faktor menampilkan variabel eksternal dipakai / di-drop (CR v3.4)", async () => {
    render(
      <ForecastResults
        data={runOf([{
          ...selected,
          method_used: "xgboost",
          hyperparameters: { exog_used: ["suhu"], exog_dropped: { promo: "missing_horizon" } },
        }])}
        products={products}
      />,
    );
    await bukaDetail("SKU-001");
    await userEvent.click(screen.getByRole("tab", { name: /faktor/i }));
    expect(await screen.findByText("Variabel eksternal dipakai 1 / 2")).toBeDefined();
    expect(screen.getByText(/nilai horizon belum lengkap/i)).toBeDefined();
  });

  it("hasil belum dipilih: info variabel eksternal tidak tampil", async () => {
    render(
      <ForecastResults
        data={runOf([{ ...pending, hyperparameters: { exog_used: ["suhu"], exog_dropped: {} } }], 1)}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: `Detail ${PID2}` }));
    await userEvent.click(screen.getByRole("tab", { name: /faktor/i }));
    expect(screen.queryByText(/variabel eksternal dipakai/i)).toBeNull();
  });

  it("produk gagal: Alert alasan + langkah perbaikan + link upload (CR v3.6 §7.2)", async () => {
    const failed: ForecastResult = {
      ...pending,
      id: "r3",
      status: "INSUFFICIENT_DATA",
      selection_status: null,
      candidates_evaluated: null,
      status_reason: "Histori 8 periode, minimal 12 periode.",
    };
    render(<ForecastResults data={runOf([failed])} />);
    await userEvent.click(screen.getByRole("button", { name: `Detail ${PID2}` }));

    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("Histori 8 periode, minimal 12 periode.")).toBeDefined();
    expect(within(dialog).getByText(/lengkapi histori demand/i)).toBeDefined();
    expect(within(dialog).getByRole("link", { name: /upload data demand/i }).getAttribute("href")).toBe("/forecast/new");
  });
});

describe("ForecastResults — metode terbaik otomatis (23 Nov 2026)", () => {
  const auto: ForecastResult = {
    ...selected,
    method_used: "xgboost",
    selection_reason: null,
    selection_analysis: {
      best_method: "xgboost",
      criteria: ["mad", "mape", "mfe"],
      decided_by: "mad",
      ranking: [],
      summary: "XGBoost dipilih sebagai metode terbaik dari 2 metode yang diuji.",
      reasons: ["MAPE 7,10%: Sangat baik."],
    },
  };

  it("sumber metode = dipilih otomatis, detail menampilkan analisis", async () => {
    render(<ForecastResults data={runOf([auto])} products={products} />);

    expect(screen.getByText(/otomatis · terbaik/i)).toBeDefined();
    await bukaDetail("SKU-001");
    expect(await screen.findByText(/kenapa xgboost terbaik/i)).toBeDefined();
  });
});
