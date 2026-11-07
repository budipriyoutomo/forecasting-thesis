"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { Override, OverrideInput } from "@/types/override";

// Audit trail satu target (append-only).
export function useAuditTrail(targetId: string | null) {
  const token = getToken();
  return useQuery<Override[]>({
    queryKey: ["overrides", targetId],
    enabled: Boolean(token && targetId),
    queryFn: async () => {
      const res = await api.overrides.list(targetId as string, token as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
  });
}

// Riwayat override reorder satu material dalam satu run (v3.3).
export function useReorderAuditTrail(runId: string | null, materialId: string | null) {
  const token = getToken();
  return useQuery<Override[]>({
    queryKey: ["overrides", "reorder", runId, materialId],
    enabled: Boolean(token && runId && materialId),
    queryFn: async () => {
      const res = await api.overrides.listReorder(runId as string, materialId as string, token as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
  });
}

export function useCreateOverride() {
  const qc = useQueryClient();
  return useMutation<Override, Error, OverrideInput>({
    mutationFn: async (input) => {
      const res = await api.overrides.create(input, getToken() as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
    onSuccess: (ov) => {
      qc.invalidateQueries({ queryKey: ["overrides"] });
      // Tabel Reorder menampilkan qty override yang berlaku (Fase 11.14).
      if (ov.target_type === "reorder_recommendation") qc.invalidateQueries({ queryKey: ["reorder-list"] });
    },
  });
}
