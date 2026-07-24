"use client";

import { useMutation } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { ReorderRecommendation } from "@/types/reorder";

// Generate + ambil rekomendasi reorder untuk satu run (Fase 5).
export function useGenerateReorder() {
  return useMutation<
    ReorderRecommendation[],
    Error,
    { runId: string; currentStock?: Record<string, number> }
  >({
    mutationFn: async ({ runId, currentStock }) => {
      const res = await api.reorder.generate(runId, currentStock ?? {}, getToken() as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
  });
}
