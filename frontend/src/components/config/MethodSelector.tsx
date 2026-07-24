"use client";

import { useEnabledMethods } from "@/hooks/useForecast";

// Label ramah untuk kode metode engine.
const LABELS: Record<string, string> = {
  ets: "ETS (Exponential Smoothing)",
  arima: "ARIMA",
  lgbm: "LightGBM",
  croston: "Croston / SBA",
  prophet: "Prophet",
};

// Dropdown "Otomatis (Direkomendasikan)" + daftar metode aktif (§6.8).
// `value === ""` berarti mode otomatis (method: null ke backend).
export function MethodSelector({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  const { data: methods, isPending } = useEnabledMethods();

  return (
    <div className="flex flex-col gap-1">
      <label htmlFor="method" className="text-sm font-medium">
        Metode forecasting
      </label>
      <select
        id="method"
        className="h-10 rounded-md border border-input bg-background px-3 text-sm"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={isPending}
      >
        <option value="">Otomatis (Direkomendasikan)</option>
        {(methods ?? []).map((m) => (
          <option key={m} value={m}>
            {LABELS[m] ?? m}
          </option>
        ))}
      </select>
    </div>
  );
}
