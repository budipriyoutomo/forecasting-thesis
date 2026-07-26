import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { InventoryMetricsTable } from "@/components/dashboard/InventoryMetricsTable";
import type { InventoryMetric } from "@/types/metrics";

const rows: InventoryMetric[] = [
  {
    target_type: "product",
    target_id: "p1",
    scope: "baseline",
    service_level: "0.9",
    fill_rate: "0.95",
    stock_out_rate: "0.1",
    inventory_turnover: "4",
  },
  {
    target_type: "product",
    target_id: "p1",
    scope: "forecastiq",
    service_level: "0.98",
    fill_rate: "0.99",
    stock_out_rate: "0.02",
    inventory_turnover: "5",
  },
];

describe("InventoryMetricsTable", () => {
  it("menampilkan baris baseline & forecastiq dengan format persen", () => {
    render(<InventoryMetricsTable metrics={rows} />);
    expect(screen.getByText(/Existing \(baseline\)/i)).toBeDefined();
    expect(screen.getByText("ForecastIQ")).toBeDefined();
    expect(screen.getByText("98.0%")).toBeDefined(); // service level forecastiq
    expect(screen.getByText("5.00×")).toBeDefined(); // turnover
  });

  it("menampilkan pesan kosong bila tak ada metrik", () => {
    render(<InventoryMetricsTable metrics={[]} />);
    expect(screen.getByText(/belum ada metrik inventory/i)).toBeDefined();
  });
});
