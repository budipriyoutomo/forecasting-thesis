"use client";

import { useMutation } from "@tanstack/react-query";

import { getToken } from "@/lib/auth";
import { downloadExport } from "@/lib/download";
import { type ExportInput, exportRequest } from "@/lib/exports";

// Export forecast (xlsx) / reorder, proyeksi stok, metrik inventory (xlsx|pdf) → unduh file.
export function useExport() {
  return useMutation<Blob, Error, ExportInput>({
    mutationFn: async (input) => {
      const { path, filename } = exportRequest(input);
      return downloadExport(path, getToken() as string, filename);
    },
  });
}
