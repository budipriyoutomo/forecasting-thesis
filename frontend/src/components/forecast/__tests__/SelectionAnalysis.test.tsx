import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SelectionAnalysis } from "@/components/forecast/SelectionAnalysis";
import type { SelectionAnalysis as Analysis } from "@/types/forecast";

const analysis: Analysis = {
  best_method: "xgboost",
  criteria: ["mad", "mape", "mfe"],
  decided_by: "mad",
  ranking: [
    { method: "xgboost", rank: 1, rank_mad: 1, rank_mfe: 1, rank_mape: 1, mad: 5, mfe: 1, mape: 8 },
    { method: "random_forest", rank: 2, rank_mad: 2, rank_mfe: 2, rank_mape: 2, mad: 7, mfe: -2, mape: 12 },
  ],
  summary: "XGBoost dipilih sebagai metode terbaik dari 2 metode yang diuji.",
  reasons: ["MAD 5,00, peringkat 1 dari 2.", "Interpretasi MAPE 8,00%: Sangat baik (skala Lewis, 1982)."],
};

describe("SelectionAnalysis (23 Nov 2026 — metode terbaik otomatis)", () => {
  it("menampilkan judul, ringkasan, kriteria, dan alasan", () => {
    render(<SelectionAnalysis analysis={analysis} methodUsed="xgboost" />);

    expect(screen.getByText(/kenapa xgboost terbaik/i)).toBeDefined();
    expect(screen.getByText(/dipilih sebagai metode terbaik/i)).toBeDefined();
    expect(screen.getByText(/urutan prioritas: 1\) MAD, 2\) MAPE, 3\) MFE/i)).toBeDefined();
    expect(screen.getByText(/penentu: MAD/i)).toBeDefined();
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
  });

  it("memberi tahu bila planner mengganti pilihan sistem", () => {
    render(<SelectionAnalysis analysis={analysis} methodUsed="random_forest" />);

    expect(screen.getByText(/diganti planner ke random forest/i)).toBeDefined();
  });

  it("tidak merender apa pun tanpa analisis (mode manual / run lama)", () => {
    const { container } = render(<SelectionAnalysis analysis={null} methodUsed="xgboost" />);

    expect(container.innerHTML).toBe("");
  });
});
