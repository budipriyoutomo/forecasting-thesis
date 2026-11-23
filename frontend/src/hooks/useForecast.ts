"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type {
  ForecastResult,
  ForecastRunInput,
  ForecastRunListItem,
  ForecastRunResponse,
  MethodComparison,
  MethodSelectionInput,
  RunSelectionResult,
} from "@/types/forecast";

// Daftar run (semua role), terbaru dulu — halaman /forecast & RunPicker (CR v3.6 §1).
export function useForecastRuns() {
  const token = getToken();
  return useQuery<ForecastRunListItem[]>({
    queryKey: ["forecast-runs"],
    enabled: Boolean(token),
    queryFn: async () => {
      const res = await api.forecast.listRuns(token as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
  });
}

export function useCreateForecastRun() {
  const qc = useQueryClient();
  return useMutation<ForecastRunResponse, Error, ForecastRunInput>({
    mutationFn: async (input) => {
      const res = await api.forecast.createRun(input, getToken() as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
    // CR v3.6 §1 — halaman detail run membaca dari cache ini tanpa fetch ulang.
    onSuccess: (data) => {
      qc.setQueryData(["forecast-run", data.run.run_id], data);
      qc.invalidateQueries({ queryKey: ["forecast-runs"] });
      qc.invalidateQueries({ queryKey: ["dashboard-summary"] });
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

// CR v3.7 — hasil per metode format thesis. Semua angka dari backend.
export function methodComparisonKey(runId: string | null) {
  return ["forecast-run", runId, "method-comparison"] as const;
}

export function useMethodComparison(runId: string | null) {
  const token = getToken();
  return useQuery<MethodComparison>({
    queryKey: methodComparisonKey(runId),
    enabled: Boolean(token && runId),
    queryFn: async () => {
      const res = await api.forecast.getMethodComparison(runId as string, token as string);
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
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["forecast-run", runId] });
      // Eksplisit (juga tercakup prefix di atas): "metode dipakai" di view thesis bisa berubah.
      qc.invalidateQueries({ queryKey: methodComparisonKey(runId) });
      qc.invalidateQueries({ queryKey: ["forecast-runs"] });
    },
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
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["forecast-run", runId] });
      // Eksplisit (juga tercakup prefix di atas): "metode dipakai" di view thesis bisa berubah.
      qc.invalidateQueries({ queryKey: methodComparisonKey(runId) });
      qc.invalidateQueries({ queryKey: ["forecast-runs"] });
    },
  });
}
