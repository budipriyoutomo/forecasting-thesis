"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type {
  ForecastResult,
  ForecastRunInput,
  ForecastRunResponse,
  MethodSelectionInput,
  RunSelectionResult,
} from "@/types/forecast";

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

// Hasil run terkini (metode berlaku sudah diterapkan backend). `initialData` = respons
// create run, supaya tidak ada fetch ulang sampai planner memilih metode (Fase 11.15).
export function useForecastRun(runId: string | null, initialData?: ForecastRunResponse) {
  const token = getToken();
  return useQuery<ForecastRunResponse>({
    queryKey: ["forecast-run", runId],
    enabled: Boolean(token && runId),
    initialData,
    queryFn: async () => {
      const res = await api.forecast.getRun(runId as string, token as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
  });
}

// Fase 11.15 — planner memilih metode satu produk / semua produk dalam run.
export function useSelectForecastMethod(runId: string | null) {
  const qc = useQueryClient();
  return useMutation<ForecastResult, Error, MethodSelectionInput & { resultId: string }>({
    mutationFn: async ({ resultId, ...input }) => {
      const res = await api.forecast.selectMethod(resultId, input, getToken() as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["forecast-run", runId] }),
  });
}

export function useSelectForecastMethodForRun(runId: string | null) {
  const qc = useQueryClient();
  return useMutation<RunSelectionResult, Error, MethodSelectionInput>({
    mutationFn: async (input) => {
      const res = await api.forecast.selectMethodForRun(runId as string, input, getToken() as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["forecast-run", runId] }),
  });
}
