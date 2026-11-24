"use client";

import { AlertTriangle } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { TableSkeleton } from "@/components/common/TableSkeleton";
import { BestMethodAnalysis } from "@/components/forecast/method-view/BestMethodAnalysis";
import { MethodForecastMatrix } from "@/components/forecast/method-view/MethodForecastMatrix";
import { MethodMetricsTable } from "@/components/forecast/method-view/MethodMetricsTable";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { useMethodComparison } from "@/hooks/useForecast";
import type { MethodComparisonMethod, MetricCriterion } from "@/types/forecast";
import type { Product } from "@/types/product";

const ANALYSIS_ID = "method-analysis";
const sectionId = (method: string) => `method-${method}`;

// CR v3.7 — langkah 1 "Forecast" format thesis "Part 1 = Forecast": section 1..N per metode
// (urutan dari backend, THESIS_METHOD_ORDER), lalu analisis pemilihan metode terbaik.
export function MethodComparisonView({ runId, products }: { runId: string; products: Product[] }) {
  const query = useMethodComparison(runId);
  if (query.isPending) return <TableSkeleton />;
  if (query.isError) return <EmptyState message={query.error.message} />;
  const data = query.data;
  if (data.methods.length === 0) {
    return <EmptyState message="Belum ada hasil per metode untuk run ini." hint="Semua produk gagal diforecast." />;
  }

  const byId = new Map(products.map((p) => [p.id, p]));
  const variantLabel = (id: string) => byId.get(id)?.code ?? id.slice(0, 8);
  const best = data.run_selection?.best_method;

  return (
    <div className="flex flex-col gap-8">
      <nav aria-label="Lompat ke metode" className="flex flex-wrap gap-2">
        {data.methods.map((m) => (
          <a key={m.method} href={`#${sectionId(m.method)}`} className={CHIP}>
            {m.label}
          </a>
        ))}
        <a href={`#${ANALYSIS_ID}`} className={CHIP}>
          Analisis
        </a>
      </nav>

      {data.methods.map((m, i) => (
        <MethodSection
          key={m.method}
          index={i + 1}
          method={m}
          isBest={m.method === best}
          periods={data.periods}
          criteria={data.criteria}
          variantLabel={variantLabel}
        />
      ))}

      <section id={ANALYSIS_ID} className="flex scroll-mt-4 flex-col gap-3">
        <h3 className="text-base font-semibold">{data.methods.length + 1}. Analisis pemilihan metode terbaik</h3>
        <BestMethodAnalysis
          selection={data.run_selection}
          criteria={data.criteria}
          productMethods={data.product_methods}
          variantLabel={variantLabel}
        />
      </section>
    </div>
  );
}

const CHIP =
  "rounded-full border px-3 py-1 text-xs font-medium hover:bg-muted focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring";

function MethodSection({
  index,
  method,
  isBest,
  periods,
  criteria,
  variantLabel,
}: {
  index: number;
  method: MethodComparisonMethod;
  isBest: boolean;
  periods: string[];
  criteria: MetricCriterion[];
  variantLabel: (productId: string) => string;
}) {
  const failedAll = method.rows.length > 0 && method.rows.every((r) => r.status === "FAILED");
  const reasons = [...new Set(method.rows.map((r) => r.reason).filter((r): r is string => !!r))];
  return (
    <section id={sectionId(method.method)} className="flex scroll-mt-4 flex-col gap-4">
      <h3 className="flex items-center gap-2 text-base font-semibold">
        {index}. Metode {method.label}
        {isBest && <Badge variant="success">Terbaik</Badge>}
        {failedAll && <Badge variant="destructive">Gagal</Badge>}
      </h3>
      {failedAll && (
        <Alert variant="warning">
          <AlertTriangle className="size-4" />
          <AlertDescription>
            Metode {method.label} aktif di Pengaturan Forecast tetapi gagal dijalankan di semua varian, sehingga
            tidak ikut dibandingkan.
            {reasons.length > 0 && <> Alasan: {reasons.join("; ")}</>}
          </AlertDescription>
        </Alert>
      )}
      <div className="flex flex-col gap-2">
        <h4 className="text-sm font-medium">a. Hasil ramalan (forecasting)</h4>
        <MethodForecastMatrix method={method} periods={periods} variantLabel={variantLabel} />
      </div>
      <div className="flex flex-col gap-2">
        <h4 className="text-sm font-medium">b. Pengujian peramalan</h4>
        <MethodMetricsTable method={method} criteria={criteria} variantLabel={variantLabel} />
      </div>
    </section>
  );
}
