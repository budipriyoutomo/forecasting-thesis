"use client";

import { MetricHeader } from "@/components/forecast/MetricHeader";
import { MetricValue } from "@/components/forecast/MetricValue";
import { NUM, STICKY } from "@/components/forecast/method-view/MethodForecastMatrix";
import { CopyTableButton } from "@/components/forecast/method-view/CopyTableButton";
import { MissingValue } from "@/components/forecast/method-view/MissingValue";
import {
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { TooltipProvider } from "@/components/ui/tooltip";
import { METRIC_INFO, formatMetric } from "@/lib/metrics";
import type { MethodComparisonMethod, MetricCriterion } from "@/types/forecast";

// CR v3.7 (b) — pengujian peramalan satu metode: varian × metrik (urutan = `criteria` backend,
// MAD · MAPE · MFE) + baris Average dari backend (MFE bertanda).
export function MethodMetricsTable({
  method,
  criteria,
  variantLabel,
}: {
  method: MethodComparisonMethod;
  criteria: MetricCriterion[];
  variantLabel: (productId: string) => string;
}) {
  const { average } = method;
  const tsv = () => [
    ["Varian", ...criteria.map((m) => METRIC_INFO[m].label)],
    ...method.rows.map((r) => [variantLabel(r.product_id), ...criteria.map((m) => formatMetric(r[m], m))]),
    ["Average", ...criteria.map((m) => formatMetric(average[m], m))],
  ];
  return (
    <TooltipProvider delayDuration={150}>
      <div className="flex justify-end">
        <CopyTableButton label={`pengujian peramalan ${method.label}`} rows={tsv} />
      </div>
      <div className="overflow-x-auto rounded-md border">
        <Table aria-label={`Pengujian peramalan ${method.label}`}>
          <TableHeader>
            <TableRow>
              <TableHead className={STICKY}>Varian</TableHead>
              {criteria.map((m) => (
                <TableHead key={m} className="text-right">
                  <MetricHeader metric={m} />
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {method.rows.map((row) => (
              <TableRow key={row.product_id}>
                <TableCell className={`${STICKY} font-medium`}>{variantLabel(row.product_id)}</TableCell>
                {criteria.map((m) => (
                  <TableCell key={m} className={NUM}>
                    {row.status === "FAILED" ? <MissingValue status="FAILED" /> : <MetricValue metric={m} value={row[m]} />}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
          <TableFooter>
            <TableRow className="font-semibold">
              <TableCell className={STICKY}>
                Average
                {average.n < average.n_total && (
                  <span className="block text-xs font-normal text-muted-foreground">
                    n = {average.n} dari {average.n_total} varian
                  </span>
                )}
              </TableCell>
              {criteria.map((m) => (
                <TableCell key={m} className={NUM}>
                  <MetricValue metric={m} value={average[m]} />
                </TableCell>
              ))}
            </TableRow>
          </TableFooter>
        </Table>
      </div>
    </TooltipProvider>
  );
}
