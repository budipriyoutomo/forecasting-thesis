"use client";

import { Area, CartesianGrid, ComposedChart, Line, ReferenceLine, XAxis, YAxis } from "recharts";

import {
  type ChartConfig,
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { formatNumber } from "@/lib/format";
import type { ForecastPoint, HistoryPoint } from "@/types/forecast";

// Warna diambil dari slot kategorikal yang sudah divalidasi (--chart-1/-2), bukan
// warna bawaan recharts. Urutan slot adalah mekanisme keamanan buta warna, jadi
// jangan ditukar. chart-1 dan chart-2 keduanya lolos kontras 3:1 di mode terang.
// Selain warna, seri dibedakan bentuk garis: aktual solid, forecast putus-putus.
const chartConfig = {
  actual: { label: "Aktual (histori)", color: "hsl(var(--chart-2))" },
  value: { label: "Forecast", color: "hsl(var(--chart-1))" },
  range: { label: "Interval keyakinan", color: "hsl(var(--chart-1))" },
} satisfies ChartConfig;

export interface ChartRow {
  date: string;
  actual: number | null;
  value: number | null;
  range: [number, number] | null;
  /** Garis penyambung histori terakhir → forecast pertama, supaya tidak ada celah. */
  bridge: number | null;
}

// CR v3.6 §7.1 — histori aktual (solid) → forecast (garis + band), dengan pemisah di titik
// mulai forecast. Fungsi murni supaya bisa dites tanpa merender recharts.
export function buildChartData(
  forecast: ForecastPoint[],
  history: HistoryPoint[] = [],
): { data: ChartRow[]; forecastStart: string | null } {
  const hist = [...history].sort((a, b) => a.date.localeCompare(b.date));
  const fc = [...forecast].sort((a, b) => a.date.localeCompare(b.date));
  const rows: ChartRow[] = [
    ...hist.map((h) => ({ date: h.date, actual: h.value, value: null, range: null, bridge: null })),
    ...fc.map((p) => ({
      date: p.date,
      actual: null,
      value: p.value,
      range: [p.lower, p.upper] as [number, number],
      bridge: null,
    })),
  ];
  if (hist.length > 0 && fc.length > 0) {
    rows[hist.length - 1].bridge = hist[hist.length - 1].value;
    rows[hist.length].bridge = fc[0].value;
  }
  return { data: rows, forecastStart: hist.length > 0 && fc.length > 0 ? fc[0].date : null };
}

export function ForecastChart({
  forecast,
  history,
}: {
  forecast: ForecastPoint[];
  history?: HistoryPoint[];
}) {
  if (forecast.length === 0) return null;
  const { data, forecastStart } = buildChartData(forecast, history);
  const hasHistory = (history?.length ?? 0) > 0;

  return (
    <ChartContainer config={chartConfig} className="h-[280px] w-full">
      <ComposedChart data={data} margin={{ top: 16, right: 8, bottom: 8, left: 8 }}>
        <CartesianGrid vertical={false} strokeDasharray="3 3" />
        <XAxis dataKey="date" tickLine={false} axisLine={false} tick={{ fontSize: 11 }} minTickGap={24} />
        <YAxis
          tickLine={false}
          axisLine={false}
          tick={{ fontSize: 11 }}
          width={52}
          tickFormatter={(v: number) => formatNumber(v, 0)}
        />
        <ChartTooltip content={<ChartTooltipContent />} />
        <Area dataKey="range" stroke="none" fill="var(--color-range)" fillOpacity={0.15} isAnimationActive={false} />
        {hasHistory && (
          <Line
            dataKey="actual"
            stroke="var(--color-actual)"
            strokeWidth={2}
            dot={false}
            connectNulls={false}
            isAnimationActive={false}
          />
        )}
        {hasHistory && (
          <Line
            dataKey="bridge"
            stroke="var(--color-value)"
            strokeWidth={2}
            strokeDasharray="5 4"
            dot={false}
            connectNulls
            legendType="none"
            tooltipType="none"
            isAnimationActive={false}
          />
        )}
        <Line
          dataKey="value"
          stroke="var(--color-value)"
          strokeWidth={2}
          strokeDasharray={hasHistory ? "5 4" : undefined}
          dot={false}
          isAnimationActive={false}
        />
        {forecastStart && (
          <ReferenceLine
            x={forecastStart}
            stroke="hsl(var(--muted-foreground))"
            strokeDasharray="2 2"
            label={{ value: "Mulai forecast", position: "insideTopLeft", fontSize: 11 }}
          />
        )}
        <ChartLegend content={<ChartLegendContent />} />
      </ComposedChart>
    </ChartContainer>
  );
}
