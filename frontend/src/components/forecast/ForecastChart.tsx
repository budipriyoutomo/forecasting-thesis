"use client";

import {
  Area,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { ForecastPoint } from "@/types/forecast";

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
  const data = forecast.map((p) => ({
    date: p.date,
    value: p.value,
    range: [p.lower, p.upper] as [number, number],
    actual: actualMap.get(p.date) ?? null,
  }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
        <XAxis dataKey="date" tick={{ fontSize: 11 }} minTickGap={24} />
        <YAxis tick={{ fontSize: 11 }} width={40} />
        <Tooltip />
        <Area
          dataKey="range"
          stroke="none"
          fill="hsl(var(--primary))"
          fillOpacity={0.12}
          isAnimationActive={false}
          name="Interval keyakinan"
        />
        <Line
          dataKey="value"
          stroke="hsl(var(--primary))"
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
          name="Forecast"
        />
        {actual && actual.length > 0 && (
          <Line
            dataKey="actual"
            stroke="hsl(var(--muted-foreground))"
            strokeWidth={1.5}
            strokeDasharray="4 3"
            dot={false}
            isAnimationActive={false}
            name="Aktual"
          />
        )}
      </ComposedChart>
    </ResponsiveContainer>
  );
}
