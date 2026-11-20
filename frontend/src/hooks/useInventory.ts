"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { ApiResponse } from "@/types/api";
import type { ImportResult } from "@/types/externalVariable";
import type { LatestStock, MaterialUsageRow, StockSnapshot, WasteFactor } from "@/types/inventory";

// Stok ERP & pemakaian aktual material (Fase 11.1/11.5). Kedatangan = hasil ROP (/material-arrivals).
const KEYS = { latest: ["stock-latest"], waste: ["waste-factors"] };

function unwrap<T>(res: ApiResponse<T>): T {
  if (!res.success) throw new Error(res.error.message);
  return res.data;
}

function useList<T>(key: string[], fetcher: (token: string) => Promise<ApiResponse<T>>) {
  const token = getToken();
  return useQuery<T>({ queryKey: key, enabled: Boolean(token), queryFn: async () => unwrap(await fetcher(token as string)) });
}

export const useLatestStock = () => useList<LatestStock[]>(KEYS.latest, api.inventory.latest);
export const useWasteFactors = () => useList<WasteFactor[]>(KEYS.waste, api.inventory.wasteFactors);

// Riwayat per material (CR v3.5 §5.2) — hanya dimuat setelah material dipilih.
function useHistory<T>(key: string, materialId: string | null, fetcher: (id: string, token: string) => Promise<ApiResponse<T>>) {
  const token = getToken();
  return useQuery<T>({
    queryKey: [key, materialId],
    enabled: Boolean(token && materialId),
    queryFn: async () => unwrap(await fetcher(materialId as string, token as string)),
  });
}

export const useStockSnapshots = (materialId: string | null) =>
  useHistory<StockSnapshot[]>(KEYS.latest[0], materialId, api.inventory.snapshots);
export const useMaterialUsage = (materialId: string | null) =>
  useHistory<MaterialUsageRow[]>(KEYS.waste[0], materialId, api.inventory.usage);

function useImport(key: string[], upload: (file: File, token: string) => Promise<ApiResponse<ImportResult>>) {
  const qc = useQueryClient();
  return useMutation<ImportResult, Error, File>({
    mutationFn: async (file) => unwrap(await upload(file, getToken() as string)),
    onSuccess: () => qc.invalidateQueries({ queryKey: key }),
  });
}

export const useImportSnapshots = () => useImport(KEYS.latest, api.inventory.importSnapshots);
export const useImportUsage = () => useImport(KEYS.waste, api.inventory.importUsage);
