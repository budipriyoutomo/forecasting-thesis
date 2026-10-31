"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { ApiResponse } from "@/types/api";
import type { ImportResult } from "@/types/externalVariable";
import type { LatestStock, MaterialReceipt, MaterialReceiptInput, WasteFactor } from "@/types/inventory";

// Stok ERP, kedatangan & pemakaian aktual material (Fase 11.1/11.5).
const KEYS = { latest: ["stock-latest"], receipts: ["material-receipts"], waste: ["waste-factors"] };

function unwrap<T>(res: ApiResponse<T>): T {
  if (!res.success) throw new Error(res.error.message);
  return res.data;
}

function useList<T>(key: string[], fetcher: (token: string) => Promise<ApiResponse<T>>) {
  const token = getToken();
  return useQuery<T>({ queryKey: key, enabled: Boolean(token), queryFn: async () => unwrap(await fetcher(token as string)) });
}

export const useLatestStock = () => useList<LatestStock[]>(KEYS.latest, api.inventory.latest);
export const useReceipts = () => useList<MaterialReceipt[]>(KEYS.receipts, api.inventory.receipts);
export const useWasteFactors = () => useList<WasteFactor[]>(KEYS.waste, api.inventory.wasteFactors);

function useImport(key: string[], upload: (file: File, token: string) => Promise<ApiResponse<ImportResult>>) {
  const qc = useQueryClient();
  return useMutation<ImportResult, Error, File>({
    mutationFn: async (file) => unwrap(await upload(file, getToken() as string)),
    onSuccess: () => qc.invalidateQueries({ queryKey: key }),
  });
}

export const useImportSnapshots = () => useImport(KEYS.latest, api.inventory.importSnapshots);
export const useImportReceipts = () => useImport(KEYS.receipts, api.inventory.importReceipts);
export const useImportUsage = () => useImport(KEYS.waste, api.inventory.importUsage);

export function useCreateReceipt() {
  const qc = useQueryClient();
  return useMutation<MaterialReceipt, Error, MaterialReceiptInput>({
    mutationFn: async (input) => unwrap(await api.inventory.createReceipt(input, getToken() as string)),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.receipts }),
  });
}

export function useDeleteReceipt() {
  const qc = useQueryClient();
  return useMutation<unknown, Error, string>({
    mutationFn: async (id) => unwrap(await api.inventory.removeReceipt(id, getToken() as string)),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.receipts }),
  });
}
