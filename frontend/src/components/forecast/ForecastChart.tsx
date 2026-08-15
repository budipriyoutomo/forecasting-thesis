"use client";

import { Area, CartesianGrid, ComposedChart, Line, XAxis, YAxis } from "recharts";

import {
  type ChartConfig,
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { formatNumber } from "@/lib/format";
import type { ForecastPoint } from "@/types/forecast";

// Warna diambil dari slot kategorikal yang sudah divalidasi (--chart-1/-2), bukan
// warna bawaan recharts. Urutan slot adalah mekanisme keamanan buta warna, jadi
// jangan ditukar. chart-1 dan chart-2 keduanya lolos kontras 3:1 di mode terang.
const chartConfig = {
  value: { label: "Forecast", color: "hsl(var(--chart-1))" },
  actual: { label: "Aktual", color: "hsl(var(--chart-2))" },
  range: { label: "Interval keyakinan", color: "hsl(var(--chart-1))" },
} satisfies ChartConfig;

// Tren forecast dengan confidence interval (band lower–upper) + garis nilai.
// `actual` opsional untuk overlay aktual vs forecast.
export function ForecastChart({
  forecast,
  actual,
}: {
  forecast: ForecastPoint[];
  actual?: { date: string; value: number }[];
}) {
  if (forecast.length === 0) return null;

  const actualMap = new Map((actual ?? []).map((a) => [a.date, a.value]));
  const hasActual = (actual?.length ?? 0) > 0;
  const data = forecast.map((p) => ({
    date: p.date,
    value: p.value,
    range: [p.lower, p.upper] as [number, number],
    actual: actualMap.get(p.date) ?? null,
  }));

  return (
    <ChartContainer config={chartConfig} className="h-[280px] w-full">
      <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
        <CartesianGrid vertical={false} strokeDasharray="3 3" />
        <XAxis
          dataKey="date"
          tickLine={false}
          axisLine={false}
          tick={{ fontSize: 11 }}
          minTickGap={24}
        />
        <YAxis
          tickLine={false}
          axisLine={false}
          tick={{ fontSize: 11 }}
          width={52}
          tickFormatter={(v: number) => formatNumber(v, 0)}
        />
        <ChartTooltip content={<ChartTooltipContent />} />
        <Area
          dataKey="range"
          stroke="none"
          fill="var(--color-range)"
          fillOpacity={0.15}
          isAnimationActive={false}
        />
        <Line
          dataKey="value"
          stroke="var(--color-value)"
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
        />
        {hasActual && (
          <Line
            dataKey="actual"
            stroke="var(--color-actual)"
            strokeWidth={2}
            strokeDasharray="4 3"
            dot={false}
            isAnimationActive={false}
          />
        )}
        <ChartLegend content={<ChartLegendContent />} />
      </ComposedChart>
    </ChartContainer>
  );
}
