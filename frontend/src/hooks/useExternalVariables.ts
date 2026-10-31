"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { ApiResponse } from "@/types/api";
import type { ExternalVariable, ExternalVariableInput, ImportResult } from "@/types/externalVariable";

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
