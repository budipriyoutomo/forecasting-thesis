"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { ReorderRecommendation } from "@/types/reorder";

// Generate + ambil rekomendasi reorder untuk satu run (Fase 5).
export function useGenerateReorder() {
  const qc = useQueryClient();
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
    // Satu sumber untuk tabel: query `reorder-list` (di-refresh setelah override, Fase 11.14).
    onSuccess: (data, { runId }) => qc.setQueryData(["reorder-list", runId], data),
  });
}
