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
