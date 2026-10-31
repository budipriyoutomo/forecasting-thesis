import { describe, expect, it } from "vitest";

import { exportRequest } from "@/lib/exports";

describe("exportRequest", () => {
  it("forecast selalu xlsx", () => {
    expect(exportRequest({ kind: "forecast", runId: "r1" })).toEqual({
      path: "/api/v1/forecast/runs/r1/export",
      filename: "forecast_r1.xlsx",
    });
  });

  it("reorder dengan format", () => {
    expect(exportRequest({ kind: "reorder", runId: "r 1", format: "pdf" })).toEqual({
      path: "/api/v1/reorder/recommendations/export?run_id=r%201&format=pdf",
      filename: "reorder_r 1.pdf",
    });
  });

  it("proyeksi stok + filter skenario", () => {
    expect(exportRequest({ kind: "stockProjection", runId: "r1", format: "xlsx", scenario: "proposed" })).toEqual({
      path: "/api/v1/forecast/runs/r1/stock-projection/export?format=xlsx&scenario=proposed",
      filename: "stock_projection_r1.xlsx",
    });
  });

  it("metrik inventory + filter target", () => {
    expect(exportRequest({ kind: "metrics", runId: "r1", format: "pdf", targetType: "material" })).toEqual({
      path: "/api/v1/forecast/runs/r1/inventory-metrics/export?format=pdf&target_type=material",
      filename: "inventory_metrics_r1.pdf",
    });
  });

  it("tanpa filter tidak menambah query kosong", () => {
    expect(exportRequest({ kind: "metrics", runId: "r1" }).path).toBe(
      "/api/v1/forecast/runs/r1/inventory-metrics/export?format=xlsx",
    );
  });
});
