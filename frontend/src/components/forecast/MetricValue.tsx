import { formatMetric, type MetricKey } from "@/lib/metrics";
import { mapeLabel } from "@/lib/mape";

// Nilai metrik pengujian peramalan (MAD, MFE, MAPE). MAPE membawa label skala Lewis —
// penilaian ABSOLUT per sel, bukan peringkat antar metode (Fase 11.15).
export function MetricValue({ metric, value }: { metric: MetricKey; value: number | null | undefined }) {
  const text = formatMetric(value, metric);
  if (value != null && metric === "mape") {
    return (
      <span className="flex flex-col">
        <span className="tabular-nums">{text}</span>
        <span className="text-xs text-muted-foreground">{mapeLabel(value)}</span>
      </span>
    );
  }
  return <span className="tabular-nums">{text}</span>;
}
