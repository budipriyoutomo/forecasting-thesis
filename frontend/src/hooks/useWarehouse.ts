"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type {
  WarehouseConfig,
  WarehouseConfigInput,
  WarehouseValidation,
} from "@/types/warehouse";

const KEY = ["warehouse-config"];

export function useWarehouseConfig() {
  const token = getToken();
  return useQuery<WarehouseConfig | null>({
    queryKey: KEY,
    enabled: Boolean(token),
    queryFn: async () => {
      const res = await api.warehouse.getConfig(token as string);
      // Belum diatur (404) bukan error fatal untuk UI — kembalikan null.
      if (!res.success) {
        if (res.error.code === "WAREHOUSE_CONFIG_NOT_FOUND") return null;
        throw new Error(res.error.message);
      }
      return res.data;
    },
  });
}

export function useSetWarehouseConfig() {
  const qc = useQueryClient();
  return useMutation<WarehouseConfig, Error, WarehouseConfigInput>({
    mutationFn: async (input) => {
      const res = await api.warehouse.setConfig(input, getToken() as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
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
