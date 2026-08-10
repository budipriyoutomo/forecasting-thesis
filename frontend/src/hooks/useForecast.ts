"use client";

import { useMutation, useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { ForecastRunInput, ForecastRunResponse, MaterialRequirement } from "@/types/forecast";

// Metode aktif untuk MethodSelector (§6.8).
export function useEnabledMethods() {
  const token = getToken();
  return useQuery<string[]>({
    queryKey: ["forecast-methods"],
    enabled: Boolean(token),
    queryFn: async () => {
      const res = await api.forecast.methods(token as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data.methods;
    },
  });
}

export function useCreateForecastRun() {
  return useMutation<ForecastRunResponse, Error, ForecastRunInput>({
    mutationFn: async (input) => {
      const res = await api.forecast.createRun(input, getToken() as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
  });
}

// Kebutuhan material hasil breakdown BOM — run-scoped, sama pola dgn useCostSummary.
export function useMaterialRequirements(runId: string | null) {
  const token = getToken();
  return useQuery<MaterialRequirement[]>({
    queryKey: ["material-requirements", runId],
    enabled: Boolean(token) && Boolean(runId),
    queryFn: async () => {
      const res = await api.forecast.materialRequirements(runId as string, token as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
  });
}
