"use client";

import { Copy } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";

/** Sel → TSV: tab antar kolom, newline antar baris (tab/newline di dalam sel jadi spasi). */
export function toTsv(rows: string[][]): string {
  return rows.map((r) => r.map((c) => c.replace(/[\t\n\r]+/g, " ")).join("\t")).join("\n");
}

// CR v3.7 D1 (P1) — salin tabel sebagai TSV supaya paste rapi ke Word/Excel thesis.
// `rows` disusun pemanggil dari data & formatter yang sama dengan tampilan (lazy).
export function CopyTableButton({ label, rows }: { label: string; rows: () => string[][] }) {
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(toTsv(rows()));
      toast.success(`Tabel ${label} disalin — tempel di Word/Excel.`);
    } catch {
      toast.error("Gagal menyalin ke clipboard. Izinkan akses clipboard di browser.");
    }
  };
  return (
    <Button type="button" variant="outline" size="sm" onClick={copy} aria-label={`Salin ${label}`}>
      <Copy />
      Salin
    </Button>
  );
}
