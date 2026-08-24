"use client";

import { Download } from "lucide-react";

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
import {
  DEMAND_TEMPLATE_COLUMNS,
  DEMAND_TEMPLATE_FILENAME,
  buildDemandTemplateCsv,
} from "@/lib/templates";

// Template unduhan supaya user tidak menebak-nebak struktur file. CSV dibangun di
// browser (bukan endpoint baru) — isinya statis dan tidak butuh data server.
export function DemandTemplateCard() {
  const onDownload = () => {
    const blob = new Blob([buildDemandTemplateCsv()], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = DEMAND_TEMPLATE_FILENAME;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex flex-col gap-1">
            <CardTitle className="text-base">Template CSV</CardTitle>
            <CardDescription>
              Unduh template, isi sesuai kolom di bawah, lalu unggah kembali. Contoh isian di
              dalam file boleh langsung ditimpa. Minimal 10 baris data agar bisa diproses.
            </CardDescription>
          </div>
          <Button variant="outline" onClick={onDownload}>
            <Download />
            Unduh template CSV
          </Button>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <div className="overflow-x-auto rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Kolom</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Keterangan</TableHead>
                <TableHead>Contoh</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {DEMAND_TEMPLATE_COLUMNS.map((c) => (
                <TableRow key={c.name}>
                  <TableCell className="whitespace-nowrap font-medium">{c.name}</TableCell>
                  <TableCell>
                    <Badge variant={c.required ? "secondary" : "outline"}>
                      {c.required ? "Wajib" : "Opsional"}
                    </Badge>
                  </TableCell>
                  <TableCell>{c.description}</TableCell>
                  <TableCell className="whitespace-nowrap tabular-nums">{c.example}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        <p className="text-sm text-muted-foreground">
          Simpan sebagai CSV dengan pemisah koma. Satu file boleh berisi banyak SKU — cukup
          tambahkan baris baru dengan <code>product_code</code> berbeda.
        </p>
      </CardContent>
    </Card>
  );
}
