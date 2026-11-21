"use client";

import { Download } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { buildTemplateCsv, type ImportTemplateSpec, type TemplateColumn } from "@/lib/templates";

function status(c: TemplateColumn): { label: string; variant: "secondary" | "outline" | "default" } {
  if (c.required) return { label: "Wajib", variant: "secondary" };
  if (c.conditional) return { label: "Bersyarat", variant: "default" };
  return { label: "Opsional", variant: "outline" };
}

// Kartu template import bersama: tombol unduh CSV + tabel kolom + catatan cara pengisian.
// Dipasang di samping setiap tombol import supaya file yang diunggah tidak melenceng.
export function ImportTemplateCard({ template }: { template: ImportTemplateSpec }) {
  const onDownload = () => {
    const blob = new Blob([buildTemplateCsv(template)], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = template.filename;
    link.click();
    URL.revokeObjectURL(url);
  };
  const buttonLabel = `Unduh ${template.title.charAt(0).toLowerCase()}${template.title.slice(1)}`;

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex flex-col gap-1">
            <CardTitle className="text-base">{template.title}</CardTitle>
            <CardDescription>
              Unduh template, isi sesuai kolom di bawah, lalu unggah kembali lewat tombol import.
            </CardDescription>
          </div>
          <Button type="button" variant="outline" onClick={onDownload}>
            <Download />
            {buttonLabel}
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
              {template.columns.map((c) => {
                const s = status(c);
                return (
                  <TableRow key={c.name}>
                    <TableCell className="whitespace-nowrap font-medium">{c.name}</TableCell>
                    <TableCell>
                      <Badge variant={s.variant}>{s.label}</Badge>
                    </TableCell>
                    <TableCell className="min-w-64 whitespace-normal">{c.description}</TableCell>
                    <TableCell className="whitespace-nowrap tabular-nums">{c.example}</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
        <div className="flex flex-col gap-1 text-sm text-muted-foreground">
          <p className="font-medium text-foreground">Cara pengisian</p>
          <ul className="list-disc space-y-1 pl-5">
            {template.notes.map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}
