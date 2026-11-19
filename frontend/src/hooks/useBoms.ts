"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { Bom, BomBulkInput, BomInput, MaterialComponent } from "@/types/bom";

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

// 19 Nov 2026 — satu produk, banyak material sekaligus
export function useCreateBomsBulk() {
  const qc = useQueryClient();
  return useMutation<Bom[], Error, BomBulkInput>({
    mutationFn: async (input) => {
      const res = await api.boms.createBulk(input, getToken() as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

// Seluruh komponen level 2+ — untuk kolom Level di tabel BOM
export function useMaterialComponents() {
  const token = getToken();
  return useQuery<MaterialComponent[]>({
    queryKey: ["material-components"],
    enabled: Boolean(token),
    queryFn: async () => {
      const res = await api.bomTree.components(token as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
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
