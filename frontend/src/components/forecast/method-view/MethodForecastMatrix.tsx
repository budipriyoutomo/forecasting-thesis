"use client";

import { MissingValue } from "@/components/forecast/method-view/MissingValue";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { TooltipProvider } from "@/components/ui/tooltip";
import { formatNumber, formatPeriodLabel } from "@/lib/format";
import type { MethodComparisonMethod } from "@/types/forecast";

export const STICKY = "sticky left-0 z-10 bg-background";
export const NUM = "text-right tabular-nums";

// CR v3.7 (a) — hasil ramalan satu metode: baris = varian, kolom = periode (+ Total backend).
// Qty bilangan bulat (D6). Tidak ada hitungan di sini.
export function MethodForecastMatrix({
  method,
  periods,
  variantLabel,
}: {
  method: MethodComparisonMethod;
  periods: string[];
  variantLabel: (productId: string) => string;
}) {
  return (
    <TooltipProvider delayDuration={150}>
      <div className="overflow-x-auto rounded-md border">
        <Table aria-label={`Hasil ramalan ${method.label}`}>
          <TableHeader>
            <TableRow>
              <TableHead className={STICKY}>Varian</TableHead>
              {periods.map((d) => (
                <TableHead key={d} className="text-right">
                  {formatPeriodLabel(d)}
                </TableHead>
              ))}
              <TableHead className="text-right">Total</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {method.rows.map((row) => (
              <TableRow key={row.product_id}>
                <TableCell className={`${STICKY} font-medium`}>{variantLabel(row.product_id)}</TableCell>
                {periods.map((d) => (
                  <TableCell key={d} className={NUM}>
                    {row.forecast[d] != null ? formatNumber(row.forecast[d], 0) : <MissingValue status={row.status} />}
                  </TableCell>
                ))}
                <TableCell className={`${NUM} font-medium`}>
                  {row.total != null ? formatNumber(row.total, 0) : <MissingValue status={row.status} />}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </TooltipProvider>
  );
}
