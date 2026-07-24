"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { Material, MaterialInput } from "@/types/material";

const KEY = ["materials"];

export function useMaterials() {
  const token = getToken();
  return useQuery<Material[]>({
    queryKey: KEY,
    enabled: Boolean(token),
    queryFn: async () => {
      const res = await api.materials.list(token as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
  });
}

export function useCreateMaterial() {
  const qc = useQueryClient();
  return useMutation<Material, Error, MaterialInput>({
    mutationFn: async (input) => {
      const res = await api.materials.create(input, getToken() as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useUpdateMaterial() {
  const qc = useQueryClient();
  return useMutation<Material, Error, { id: string; input: Partial<MaterialInput> }>({
    mutationFn: async ({ id, input }) => {
      const res = await api.materials.update(id, input, getToken() as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useDeleteMaterial() {
  const qc = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: async (id) => {
      const res = await api.materials.remove(id, getToken() as string);
      if (!res.success) throw new Error(res.error.message);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
