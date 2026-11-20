"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { getToken } from "@/lib/auth";
import { downloadExport } from "@/lib/download";
import type { ApiResponse } from "@/types/api";
import type {
  ExternalVariable,
  ExternalVariableCoverage,
  ExternalVariableValue,
  ExternalVariableInput,
  ImportDryRunResult,
  ImportResult,
} from "@/types/externalVariable";

const KEY = ["external-variables"];

function unwrap<T>(res: ApiResponse<T>): T {
  if (!res.success) throw new Error(res.error.message);
  return res.data;
}

export function useExternalVariables() {
  const token = getToken();
  return useQuery<ExternalVariable[]>({
    queryKey: KEY,
    enabled: Boolean(token),
    queryFn: async () => unwrap(await api.externalVariables.list(token as string)),
  });
}

/** CR v3.4 §4.2 — kelengkapan nilai vs periode demand + horizon (bulan). Key di bawah KEY
 * supaya ikut di-refresh setiap invalidate (import, hapus nilai, toggle). */
export function useExternalVariableCoverage(horizon = 12) {
  const token = getToken();
  return useQuery<ExternalVariableCoverage[]>({
    queryKey: [...KEY, "coverage", horizon],
    enabled: Boolean(token),
    queryFn: async () => unwrap(await api.externalVariables.coverage(horizon, token as string)),
  });
}

// Nilai per periode satu variabel (CR v3.5 §5.2) — dimuat saat dialog "Lihat nilai" dibuka.
export function useExternalVariableValues(id: string | null) {
  const token = getToken();
  return useQuery<ExternalVariableValue[]>({
    queryKey: [...KEY, "values", id],
    enabled: Boolean(token && id),
    queryFn: async () => unwrap(await api.externalVariables.values(id as string, token as string)),
  });
}

export function useSaveExternalVariable() {
  const qc = useQueryClient();
  return useMutation<ExternalVariable, Error, { id?: string; input: ExternalVariableInput }>({
    mutationFn: async ({ id, input }) => {
      const token = getToken() as string;
      return unwrap(
        id ? await api.externalVariables.update(id, input, token) : await api.externalVariables.create(input, token),
      );
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useDeleteExternalVariable() {
  const qc = useQueryClient();
  return useMutation<unknown, Error, { id: string; valuesOnly?: boolean }>({
    mutationFn: async ({ id, valuesOnly }) => {
      const token = getToken() as string;
      return valuesOnly
        ? unwrap(await api.externalVariables.clearValues(id, token))
        : unwrap(await api.externalVariables.remove(id, token));
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useImportExternalValues() {
  const qc = useQueryClient();
  return useMutation<ImportResult, Error, File>({
    mutationFn: async (file) => unwrap(await api.externalVariables.importValues(file, getToken() as string)),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

/** CR v3.4 §4.3 — validasi file (dry-run): kumpulkan semua error, tidak menyimpan apa pun. */
export function useValidateExternalValues() {
  return useMutation<ImportDryRunResult, Error, File>({
    mutationFn: async (file) => unwrap(await api.externalVariables.validateValues(file, getToken() as string)),
  });
}

/** CR v3.4 §4.3 — unduh template import format lebar (.xlsx): variabel aktif × periode demand + horizon. */
export function useDownloadExternalTemplate(horizon = 12) {
  return useMutation<Blob, Error, void>({
    mutationFn: () =>
      downloadExport(
        `/api/v1/external-variables/template?horizon=${horizon}`,
        getToken() as string,
        "template_variabel_eksternal.xlsx",
      ),
  });
}
