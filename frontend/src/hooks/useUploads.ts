"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { UploadResponseData, UploadSessionSummary } from "@/types/upload";

const KEY = ["uploads"];

export function useUploadHistory() {
  const token = getToken();
  return useQuery<UploadSessionSummary[]>({
    queryKey: KEY,
    enabled: Boolean(token),
    queryFn: async () => {
      const res = await api.uploads.list(token as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
  });
}

export function useUploadFile() {
  const qc = useQueryClient();
  return useMutation<UploadResponseData, Error, File>({
    mutationFn: async (file) => {
      const res = await api.uploads.create(file, getToken() as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
