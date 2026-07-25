"use client";

import { useMutation } from "@tanstack/react-query";

import { getToken } from "@/lib/auth";
import { downloadExport } from "@/lib/download";

// Export forecast (xlsx) / reorder (xlsx|pdf) → unduh file.
export function useExport() {
  return useMutation<Blob, Error, { kind: "forecast" | "reorder"; runId: string; format?: "xlsx" | "pdf" }>({
    mutationFn: async ({ kind, runId, format = "xlsx" }) => {
      const token = getToken() as string;
      if (kind === "forecast") {
        return downloadExport(`/api/v1/forecast/runs/${runId}/export`, token, `forecast_${runId}.xlsx`);
      }
      return downloadExport(
        `/api/v1/reorder/recommendations/export?run_id=${encodeURIComponent(runId)}&format=${format}`,
        token,
        `reorder_${runId}.${format}`,
      );
    },
  });
}
