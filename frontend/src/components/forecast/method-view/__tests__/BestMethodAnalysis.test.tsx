import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { BestMethodAnalysis } from "@/components/forecast/method-view/BestMethodAnalysis";

import { COMPARISON, variantLabel } from "./fixture";

const props = {
  selection: COMPARISON.run_selection,
  criteria: COMPARISON.criteria,
  productMethods: COMPARISON.product_methods,
  variantLabel,
};

describe("BestMethodAnalysis (CR v3.7 §6)", () => {
  it("tabel peringkat: baris #1 = best_method dengan badge Terbaik", () => {
    render(<BestMethodAnalysis {...props} />);
    const table = screen.getByRole("table", { name: /peringkat metode/i });
    const first = within(table).getAllByRole("row")[1];
    expect(first.textContent).toMatch(/Random Forest/);
    expect(within(first).getByText("Terbaik")).toBeDefined();
    expect(first.getAttribute("data-best")).toBe("true");
    expect(within(table).getAllByRole("columnheader").map((h) => h.textContent)).toEqual([
      "Peringkat", "Metode", "Avg MAD", "Avg MAPE", "Avg MFE", "Varian",
    ]);
  });

  it("kesimpulan backend + urutan prioritas & penentu", () => {
    render(<BestMethodAnalysis {...props} />);
    expect(screen.getByText(COMPARISON.run_selection!.summary)).toBeDefined();
    expect(screen.getByText("Rata-rata MAD terkecil.")).toBeDefined();
    expect(screen.getByText(/urutan prioritas: 1\) MAD, 2\) MAPE, 3\) MFE · penentu: MAD/i)).toBeDefined();
  });

  it("peringatan coverage hanya bila ranking_basis = common", () => {
    const { rerender } = render(<BestMethodAnalysis {...props} />);
    expect(screen.getByRole("alert").textContent).toMatch(/LSTM/);
    rerender(
      <BestMethodAnalysis {...props} selection={{ ...COMPARISON.run_selection!, ranking_basis: "all", excluded_methods: [] }} />,
    );
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("tabel varian → metode: 'diganti planner' bila method_used ≠ pilihan sistem", () => {
    render(<BestMethodAnalysis {...props} />);
    const table = screen.getByRole("table", { name: /metode per varian/i });
    const sb = within(table).getAllByRole("row").find((r) => r.textContent?.startsWith("SB"))!;
    expect(sb.textContent).toMatch(/Moving Average/);
    expect(within(sb).getByText(/diganti planner/i)).toBeDefined();
    const pl = within(table).getAllByRole("row").find((r) => r.textContent?.startsWith("PL"))!;
    expect(within(pl).queryByText(/diganti planner/i)).toBeNull();
  });

  it("catatan metodologis skala MAD", () => {
    render(<BestMethodAnalysis {...props} />);
    expect(screen.getByText(/MAPE.*skala/i)).toBeDefined();
  });

  it("tanpa run_selection → keadaan kosong", () => {
    render(<BestMethodAnalysis {...props} selection={null} />);
    expect(screen.getByText(/belum ada metode yang berhasil diuji/i)).toBeDefined();
  });
});
