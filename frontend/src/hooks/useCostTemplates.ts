"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { CostTemplate, CostTemplateInput, CostTemplateSummary } from "@/types/costTemplate";

const KEY = ["cost-templates"];

export function useCostTemplates() {
  const token = getToken();
  return useQuery<CostTemplate[]>({
    queryKey: KEY,
    enabled: Boolean(token),
    queryFn: async () => {
      const res = await api.costTemplates.list(token as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
  });
}

export function useCostTemplateSummary(id: string | null) {
  const token = getToken();
  return useQuery<CostTemplateSummary>({
    queryKey: [...KEY, id, "summary"],
    enabled: Boolean(token && id),
    queryFn: async () => {
      const res = await api.costTemplates.summary(id as string, token as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
  });
}

export function useCreateCostTemplate() {
  const qc = useQueryClient();
  return useMutation<CostTemplate, Error, CostTemplateInput>({
    mutationFn: async (input) => {
      const res = await api.costTemplates.create(input, getToken() as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useUpdateCostTemplate() {
  const qc = useQueryClient();
  return useMutation<CostTemplate, Error, { id: string; input: CostTemplateInput }>({
    mutationFn: async ({ id, input }) => {
      const res = await api.costTemplates.update(id, input, getToken() as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useActivateCostTemplate() {
  const qc = useQueryClient();
  return useMutation<CostTemplate, Error, string>({
    mutationFn: async (id) => {
      const res = await api.costTemplates.activate(id, getToken() as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useDeleteCostTemplate() {
  const qc = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: async (id) => {
      const res = await api.costTemplates.remove(id, getToken() as string);
      if (!res.success) throw new Error(res.error.message);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
