"use client";

import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { useUploadFile } from "@/hooks/useUploads";
import type { UploadResponseData } from "@/types/upload";

// Panel upload CSV konsumsi + preview hasil validasi (Fase 3).
export function UploadPanel() {
  const upload = useUploadFile();
  const inputRef = useRef<HTMLInputElement>(null);
  const [result, setResult] = useState<UploadResponseData | null>(null);

  const onChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setResult(null);
    upload.mutate(file, { onSuccess: setResult });
  };

  const previewColumns = result?.preview?.[0] ? Object.keys(result.preview[0]) : [];

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          className="hidden"
          aria-label="Pilih file CSV"
          onChange={onChange}
        />
        <Button onClick={() => inputRef.current?.click()} disabled={upload.isPending}>
          {upload.isPending ? "Mengunggah…" : "Pilih file CSV"}
        </Button>
      </div>

      {upload.isError && <p className="text-sm text-destructive">{upload.error.message}</p>}

      {result && (
        <div className="flex flex-col gap-3 rounded-lg border p-4">
          <p className="text-sm">
            <span className="font-medium">{result.n_rows}</span> baris ·{" "}
            <span className="font-medium">{result.n_products_detected}</span> produk terdeteksi ·
            status <span className="font-medium">{result.status}</span>
          </p>

          {result.warnings.length > 0 && (
            <ul className="list-inside list-disc text-sm text-amber-600">
              {result.warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          )}

          {previewColumns.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    {previewColumns.map((c) => (
                      <th key={c} className="py-2 pr-4">
                        {c}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.preview.map((row, i) => (
                    <tr key={i} className="border-b">
                      {previewColumns.map((c) => (
                        <td key={c} className="py-2 pr-4">
                          {String(row[c] ?? "")}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
