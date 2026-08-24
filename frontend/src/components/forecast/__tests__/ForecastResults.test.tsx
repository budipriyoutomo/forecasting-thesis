import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ForecastResults } from "@/components/forecast/ForecastResults";
import type { ForecastRunResponse } from "@/types/forecast";
import type { Product } from "@/types/product";

const PID = "11111111-1111-1111-1111-111111111111";

const products: Product[] = [
  { id: PID, code: "SKU-001", name: "Kursi Lipat", category: null, unit: "pcs" },
];

const data: ForecastRunResponse = {
  run: {
    run_id: "run1",
    status: "COMPLETED",
    horizon: 3,
    horizon_unit: "days",
    n_products: 1,
    n_completed: 1,
    n_failed: 0,
  },
  results: [
    {
      product_id: PID,
      status: "COMPLETED",
      method_used: "moving_average",
      selection_mode: "auto",
      mad: null,
      mfe: null,
      mse: null,
      mape: 8.2,
      mase: null,
      candidates_evaluated: null,
      explanation: null,
      forecast: [{ date: "2026-09-01", value: 100, lower: 90, upper: 110 }],
      metrics: null,
    },
  ],
};

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
});
