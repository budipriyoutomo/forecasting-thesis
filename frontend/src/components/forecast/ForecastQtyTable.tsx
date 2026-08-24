"use client";

import { ChevronRight } from "lucide-react";

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatNumber } from "@/lib/format";
import type { ForecastPoint } from "@/types/forecast";

// Angka forecast produk: grafik saja tidak cukup untuk planner yang perlu qty pasti
// per periode (dan totalnya) sebelum membuat rencana produksi/order.
export function ForecastQtyTable({ forecast }: { forecast: ForecastPoint[] }) {
  if (forecast.length === 0) return null;

  const total = forecast.reduce((sum, p) => sum + p.value, 0);
  const average = total / forecast.length;

  return (
    <div className="flex flex-col gap-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-lg border p-3">
          <p className="text-xs text-muted-foreground">Total qty forecast ({forecast.length} periode)</p>
          <p className="text-xl font-semibold tabular-nums">{formatNumber(total)}</p>
        </div>
        <div className="rounded-lg border p-3">
          <p className="text-xs text-muted-foreground">Rata-rata per periode</p>
          <p className="text-xl font-semibold tabular-nums">{formatNumber(average)}</p>
        </div>
      </div>

      <Collapsible className="rounded-lg border">
        <CollapsibleTrigger className="group flex w-full items-center gap-2 p-3 text-sm font-medium hover:bg-muted/50">
          <ChevronRight className="size-4 transition-transform group-data-[state=open]:rotate-90" />
          Rincian qty per periode ({forecast.length})
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="overflow-x-auto border-t">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Periode</TableHead>
                  <TableHead className="text-right">Qty forecast</TableHead>
                  <TableHead className="text-right">Batas bawah</TableHead>
                  <TableHead className="text-right">Batas atas</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {forecast.map((p) => (
                  <TableRow key={p.date}>
                    <TableCell>{p.date}</TableCell>
                    <TableCell className="text-right font-medium tabular-nums">
                      {formatNumber(p.value)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{formatNumber(p.lower)}</TableCell>
                    <TableCell className="text-right tabular-nums">{formatNumber(p.upper)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
}
