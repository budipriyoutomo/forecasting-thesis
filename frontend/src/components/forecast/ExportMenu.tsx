"use client";

import { ChevronDown, Download } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { ExportInput } from "@/lib/exports";

// CR v3.6 §4 — semua export run dikumpulkan di satu dropdown "Export ▾" di header detail run.
// Export turunan perencanaan (reorder/proyeksi/metrik) nonaktif sampai perencanaan dijalankan.
export function ExportMenu({
  runId,
  hasPlanning,
  pending,
  onExport,
}: {
  runId: string;
  hasPlanning: boolean;
  pending?: boolean;
  onExport: (input: ExportInput) => void;
}) {
  const planned = (label: string) => (hasPlanning ? label : `${label} — jalankan perencanaan dulu`);
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" disabled={pending}>
          <Download />
          Export
          <ChevronDown className="opacity-60" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-72">
        <DropdownMenuLabel>Forecast</DropdownMenuLabel>
        <DropdownMenuItem onSelect={() => onExport({ kind: "forecast", runId })}>Forecast (Excel)</DropdownMenuItem>
        <DropdownMenuSeparator />
        {(
          [
            ["reorder", "Reorder"],
            ["stockProjection", "Proyeksi stok"],
            ["metrics", "Metrik inventory"],
          ] as const
        ).map(([kind, label]) => (
          <div key={kind}>
            <DropdownMenuLabel>{label}</DropdownMenuLabel>
            {(["xlsx", "pdf"] as const).map((format) => (
              <DropdownMenuItem
                key={format}
                disabled={!hasPlanning}
                onSelect={() => onExport({ kind, runId, format })}
              >
                {planned(`${label} (${format === "xlsx" ? "Excel" : "PDF"})`)}
              </DropdownMenuItem>
            ))}
          </div>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
