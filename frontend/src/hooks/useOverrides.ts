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

export function useCreateOverride() {
  const qc = useQueryClient();
  return useMutation<Override, Error, OverrideInput>({
    mutationFn: async (input) => {
      const res = await api.overrides.create(input, getToken() as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
    onSuccess: (ov) => qc.invalidateQueries({ queryKey: ["overrides", ov.target_id] }),
  });
}
