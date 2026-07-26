"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { CostSummary, InventoryMetric } from "@/types/metrics";

// Biaya & metrik inventory bersifat run-scoped — di-fetch di halaman hasil forecast.
export function useCostSummary(runId: string | null) {
  const token = getToken();
  return useQuery<CostSummary>({
    queryKey: ["cost-summary", runId],
    enabled: Boolean(token) && Boolean(runId),
    queryFn: async () => {
      const res = await api.metrics.costSummary(runId as string, token as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
  });
}

export function useInventoryMetrics(runId: string | null) {
  const token = getToken();
  return useQuery<InventoryMetric[]>({
    queryKey: ["inventory-metrics", runId],
    enabled: Boolean(token) && Boolean(runId),
    queryFn: async () => {
      const res = await api.metrics.inventory(runId as string, token as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
  });
}
