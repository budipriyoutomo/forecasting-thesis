import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CostSummaryCard } from "@/components/dashboard/CostSummaryCard";

const summary = {
  run_id: "r1",
  total_ordering_cost: "100",
  total_holding_cost: "20",
  total_inventory_cost: "80",
  baseline_inventory_cost: "100",
  savings_pct: "20",
};

describe("CostSummaryCard", () => {
  it("menampilkan TIC ForecastIQ, baseline, dan % penghematan", () => {
    render(<CostSummaryCard summary={summary} />);
    expect(screen.getByText(/TIC ForecastIQ/i)).toBeDefined();
    expect(screen.getByText(/TIC Existing/i)).toBeDefined();
    expect(screen.getByText("20.0%")).toBeDefined();
  });

  it("menandai penghematan negatif sebagai urgent", () => {
    render(<CostSummaryCard summary={{ ...summary, savings_pct: "-5" }} />);
    const value = screen.getByText("-5.0%");
    expect(value.className).toContain("text-destructive");
  });
});

describe("CostSummaryCard — template biaya & biaya pembelian (Fase 10)", () => {
  it("menyebut template biaya aktif sebagai sumber S & H", () => {
    render(
      <CostSummaryCard
        summary={{ ...summary, cost_source: "template", cost_template_name: "Template 2026" }}
      />,
    );
    expect(screen.getByText(/template biaya: template 2026/i)).toBeDefined();
  });

  it("menyebut biaya default sistem bila tanpa template aktif", () => {
    render(<CostSummaryCard summary={{ ...summary, cost_source: "env", cost_template_name: null }} />);
    expect(screen.getByText(/biaya default sistem/i)).toBeDefined();
  });

  it("biaya pembelian tampil sebagai informasi di luar TIC + peringatan material tanpa harga", () => {
    render(
      <CostSummaryCard
        summary={{ ...summary, purchase_cost: "60000", n_materials_without_price: 2, cost_source: "env" }}
      />,
    );
    expect(screen.getByText(/biaya pembelian material/i)).toBeDefined();
    expect(screen.getByText("Rp 60.000")).toBeDefined();
    expect(screen.getByText(/tidak termasuk tic/i)).toBeDefined();
    expect(screen.getByText(/2 material belum punya harga/i)).toBeDefined();
  });

  it("tanpa field Fase 10 (respons lama) kartu tetap tampil seperti semula", () => {
    render(<CostSummaryCard summary={summary} />);
    expect(screen.queryByText(/biaya pembelian material/i)).toBeNull();
  });
});

describe("CostSummaryCard — shortage cost & metode EOQ (Fase 11)", () => {
  it("menampilkan biaya kekurangan usulan vs existing dan metode EOQ", async () => {
    const { render, screen } = await import("@testing-library/react");
    const { CostSummaryCard } = await import("@/components/dashboard/CostSummaryCard");
    render(
      <CostSummaryCard
        summary={{
          run_id: "r1", total_ordering_cost: "1", total_holding_cost: "1", total_inventory_cost: "2",
          baseline_inventory_cost: "4", savings_pct: "50", eoq_method: "classic",
          shortage_cost: "700000", baseline_shortage_cost: "2100000",
        }}
      />,
    );
    expect(screen.getByText(/biaya kekurangan forecastiq/i)).toBeDefined();
    expect(screen.getByText(/2\.100\.000/)).toBeDefined();
    expect(screen.getByText(/eoq klasik/i)).toBeDefined();
  });
});
