// Path endpoint export (file biner) + nama fallback per jenis export.
export type ExportFormat = "xlsx" | "pdf";

export type ExportInput =
  | { kind: "forecast"; runId: string }
  | { kind: "reorder"; runId: string; format?: ExportFormat }
  | { kind: "stockProjection"; runId: string; format?: ExportFormat; scenario?: "proposed" | "baseline" }
  | { kind: "metrics"; runId: string; format?: ExportFormat; targetType?: "product" | "material" };

function query(params: Record<string, string | undefined>): string {
  return Object.entries(params)
    .filter(([, value]) => value)
    .map(([key, value]) => `${key}=${encodeURIComponent(value as string)}`)
    .join("&");
}

export function exportRequest(input: ExportInput): { path: string; filename: string } {
  const run = encodeURIComponent(input.runId);
  if (input.kind === "forecast") {
    return { path: `/api/v1/forecast/runs/${run}/export`, filename: `forecast_${input.runId}.xlsx` };
  }
  const format = input.format ?? "xlsx";
  if (input.kind === "reorder") {
    return {
      path: `/api/v1/reorder/recommendations/export?${query({ run_id: input.runId, format })}`,
      filename: `reorder_${input.runId}.${format}`,
    };
  }
  if (input.kind === "stockProjection") {
    return {
      path: `/api/v1/forecast/runs/${run}/stock-projection/export?${query({ format, scenario: input.scenario })}`,
      filename: `stock_projection_${input.runId}.${format}`,
    };
  }
  return {
    path: `/api/v1/forecast/runs/${run}/inventory-metrics/export?${query({ format, target_type: input.targetType })}`,
    filename: `inventory_metrics_${input.runId}.${format}`,
  };
}
