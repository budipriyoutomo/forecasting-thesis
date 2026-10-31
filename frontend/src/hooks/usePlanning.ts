"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { BomTreeNode } from "@/components/boms/BomTree";
import type { ApiResponse } from "@/types/api";
import type { PlanningSummary, StockProjectionRow } from "@/types/planning";
import type { ReorderRecommendation } from "@/types/reorder";

function unwrap<T>(res: ApiResponse<T>): T {
  if (!res.success) throw new Error(res.error.message);
  return res.data;
}

// Pipeline thesis tahap 2→4 untuk satu run (Fase 11.8). Hasil tiap tahap dibaca ulang
// lewat query masing-masing, jadi semua query run-scoped di-invalidate setelah selesai.
export function useRunPlanning() {
  const qc = useQueryClient();
  return useMutation<PlanningSummary, Error, { runId: string; currentStock?: Record<string, number> | null }>({
    mutationFn: async ({ runId, currentStock }) =>
      unwrap(await api.planning.run(runId, currentStock ?? null, getToken() as string)),
    onSuccess: (_, { runId }) => {
      for (const key of ["stock-projection", "reorder-list", "cost-summary", "inventory-metrics"])
        qc.invalidateQueries({ queryKey: [key, runId] });
    },
  });
}

export function useStockProjection(runId: string | null) {
  const token = getToken();
  return useQuery<StockProjectionRow[]>({
    queryKey: ["stock-projection", runId],
    enabled: Boolean(token && runId),
    queryFn: async () => unwrap(await api.planning.projection(runId as string, token as string)),
  });
}

export function useReorderList(runId: string | null) {
  const token = getToken();
  return useQuery<ReorderRecommendation[]>({
    queryKey: ["reorder-list", runId],
    enabled: Boolean(token && runId),
    queryFn: async () => unwrap(await api.reorder.list(runId as string, null, token as string)),
  });
}

export function useBomTree(productId: string | null) {
  const token = getToken();
  return useQuery<BomTreeNode>({
    queryKey: ["bom-tree", productId],
    enabled: Boolean(token && productId),
    queryFn: async () => unwrap(await api.bomTree.get(productId as string, token as string)),
  });
}

export function useBomComponent() {
  const qc = useQueryClient();
  return useMutation<unknown, Error, { parentId: string; componentId: string; qty: number } | { removeId: string }>({
    mutationFn: async (input) => {
      const token = getToken() as string;
      return "removeId" in input
        ? unwrap(await api.bomTree.removeComponent(input.removeId, token))
        : unwrap(await api.bomTree.addComponent(input.parentId, input.componentId, input.qty, token));
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["bom-tree"] }),
  });
}
