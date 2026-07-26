"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { Bom, BomInput } from "@/types/bom";

const KEY = ["boms"];

export function useBoms(productId: string | null = null) {
  const token = getToken();
  return useQuery<Bom[]>({
    queryKey: [...KEY, productId],
    enabled: Boolean(token),
    queryFn: async () => {
      const res = await api.boms.list(productId, token as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
  });
}

export function useCreateBom() {
  const qc = useQueryClient();
  return useMutation<Bom, Error, BomInput>({
    mutationFn: async (input) => {
      const res = await api.boms.create(input, getToken() as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useUpdateBom() {
  const qc = useQueryClient();
  return useMutation<Bom, Error, { id: string; input: Partial<BomInput> }>({
    mutationFn: async ({ id, input }) => {
      const res = await api.boms.update(id, input, getToken() as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useDeleteBom() {
  const qc = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: async (id) => {
      const res = await api.boms.remove(id, getToken() as string);
      if (!res.success) throw new Error(res.error.message);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
