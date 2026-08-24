"use client";

import { TriangleAlert, Upload } from "lucide-react";
import { useRef, useState } from "react";

import { FormError } from "@/components/common/FormError";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatNumber } from "@/lib/format";
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
      <Card className="border-dashed">
        <CardContent className="flex flex-col items-center gap-3 py-8 text-center">
          <Upload className="size-8 text-muted-foreground" />
          <div className="flex flex-col gap-1">
            <p className="text-sm font-medium">Unggah CSV histori demand</p>
            <p className="text-sm text-muted-foreground">
              Kolom wajib: product_code, period, actual. Opsional: forecast_existing, planning.
            </p>
          </div>
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
        </CardContent>
      </Card>

      <FormError message={upload.isError ? upload.error.message : null} />

      {result && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Hasil validasi</CardTitle>
            <CardDescription className="flex flex-wrap items-center gap-2">
              <Badge variant="secondary">{formatNumber(result.n_rows)} baris</Badge>
              <Badge variant="secondary">
                {formatNumber(result.n_products_detected)} produk terdeteksi
              </Badge>
              <Badge variant={result.status === "validated" ? "secondary" : "outline"}>
                {result.status}
              </Badge>
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {result.warnings.length > 0 && (
              <Alert>
                <TriangleAlert className="size-4" />
                <AlertTitle>Peringatan</AlertTitle>
                <AlertDescription>
                  <ul className="list-inside list-disc">
                    {result.warnings.map((w, i) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </AlertDescription>
              </Alert>
            )}

            {previewColumns.length > 0 && (
              <div className="overflow-x-auto rounded-lg border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      {previewColumns.map((c) => (
                        <TableHead key={c} className="whitespace-nowrap">
                          {c}
                        </TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {result.preview.map((row, i) => (
                      <TableRow key={i}>
                        {previewColumns.map((c) => (
                          <TableCell key={c} className="whitespace-nowrap">
                            {String(row[c] ?? "")}
                          </TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
