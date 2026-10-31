import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PlanningSummaryCard } from "@/components/planning/PlanningSummaryCard";

describe("PlanningSummaryCard", () => {
  it("merangkum 4 tahap alur thesis", () => {
    render(
      <PlanningSummaryCard
        summary={{
          reorder: { n_materials: 3, n_urgent: 1, n_missing_data: 1 },
          projection: { n_rows: 6, n_over_capacity: 2, n_shortage_periods: 1, baseline_available: false },
          evaluation: { n_material_metrics: 3, n_product_metrics: 6 },
          cost: { total_inventory_cost: 1, baseline_inventory_cost: 2, savings_pct: 50, shortage_cost: 0,
                  baseline_shortage_cost: 10, eoq_method: "classic" },
        }}
      />,
    );
    expect(screen.getByText(/3 material/i)).toBeDefined();
    expect(screen.getByText(/1 material datanya belum lengkap/i)).toBeDefined();
    expect(screen.getByText(/2 periode melebihi kapasitas/i)).toBeDefined();
    expect(screen.getByText(/planning horizon tidak tersedia/i)).toBeDefined();
    expect(screen.getByText("50.0%")).toBeDefined();
  });
});
