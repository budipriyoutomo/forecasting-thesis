"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { WarehouseConfig, WarehouseConfigInput, WarehouseValidation } from "@/types/warehouse";

const KEY = ["warehouse-config"];

export function useWarehouseConfigs() {
  const token = getToken();
  return useQuery<WarehouseConfig[]>({
    queryKey: KEY,
    enabled: Boolean(token),
    queryFn: async () => {
      const res = await api.warehouse.list(token as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
  });
}

export function useCreateWarehouseConfig() {
  const qc = useQueryClient();
  return useMutation<WarehouseConfig, Error, WarehouseConfigInput>({
    mutationFn: async (input) => {
      const res = await api.warehouse.create(input, getToken() as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useUpdateWarehouseConfig() {
  const qc = useQueryClient();
  return useMutation<WarehouseConfig, Error, { id: string; capacity_qty: number }>({
    mutationFn: async ({ id, capacity_qty }) => {
      const res = await api.warehouse.update(id, capacity_qty, getToken() as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useDeleteWarehouseConfig() {
  const qc = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: async (id) => {
      const res = await api.warehouse.remove(id, getToken() as string);
      if (!res.success) throw new Error(res.error.message);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

// Validasi kapasitas untuk satu run (dipicu manual dari halaman hasil forecast).
export function useWarehouseValidation() {
  return useMutation<WarehouseValidation, Error, string>({
    mutationFn: async (runId) => {
      const res = await api.warehouse.validateRun(runId, getToken() as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
  });
}
