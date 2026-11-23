import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { GlobalSelectionPanel, globalAnalysis } from "@/components/forecast/GlobalSelectionPanel";
import type { ForecastResult, SelectionAnalysis } from "@/types/forecast";

// 23 Nov 2026 — metode terbaik dipilih untuk SELURUH produk dari rata-rata pengujian.
const analysis: SelectionAnalysis = {
  scope: "global",
  n_products: 3,
  excluded_methods: ["lstm"],
  best_method: "xgboost",
  criteria: ["mad", "mape", "mfe"],
  decided_by: "mad",
  ranking: [
    { method: "xgboost", rank: 1, mad: 5, mfe: 1, mape: 8, n_products: 3 },
    { method: "random_forest", rank: 2, mad: 7, mfe: -2, mape: 12, n_products: 3 },
  ],
  summary: "XGBoost dipilih sebagai metode terbaik untuk seluruh 3 produk.",
  reasons: ["Prioritas 1 — Rata-rata MAD 5,00, peringkat 1 dari 2."],
};

const result = (a: SelectionAnalysis | null, status: ForecastResult["status"] = "COMPLETED") =>
  ({ status, selection_analysis: a }) as ForecastResult;

describe("GlobalSelectionPanel", () => {
  it("menampilkan metode terbaik seluruh produk + tabel rata-rata pengujian", () => {
    render(<GlobalSelectionPanel analysis={analysis} />);

    expect(screen.getByText(/metode terbaik untuk seluruh produk: xgboost/i)).toBeDefined();
    expect(screen.getByText(/rata-rata pengujian 3 produk/i)).toBeDefined();
    const rows = screen.getAllByRole("row");
    expect(rows).toHaveLength(3); // header + 2 metode
    expect(within(rows[1]).getByText("XGBoost")).toBeDefined();
    expect(within(rows[1]).getByText("terbaik")).toBeDefined();
    expect(within(rows[1]).getByText("5.00")).toBeDefined();
    expect(screen.getByText(/Prioritas 1 — Rata-rata MAD/)).toBeDefined();
  });

  it("globalAnalysis mengambil analisis global dari hasil run; run lama → null", () => {
    expect(globalAnalysis([result(null, "INSUFFICIENT_DATA"), result(analysis)])).toBe(analysis);
    expect(globalAnalysis([result({ ...analysis, scope: undefined })])).toBeNull();
    expect(globalAnalysis([])).toBeNull();
  });
});
