"use client";

import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useEnabledMethods } from "@/hooks/useForecast";

// Label ramah untuk kode metode engine.
const LABELS: Record<string, string> = {
  ets: "ETS (Exponential Smoothing)",
  arima: "ARIMA",
  lgbm: "LightGBM",
  croston: "Croston / SBA",
  prophet: "Prophet",
};

// Radix Select tidak menerima value "" untuk item, sementara kontrak komponen ini
// tetap memakai "" sebagai penanda mode otomatis (method: null ke backend).
const OTOMATIS = "__otomatis__";

// Dropdown "Otomatis (Direkomendasikan)" + daftar metode aktif (§6.8).
export function MethodSelector({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  const { data: methods, isPending } = useEnabledMethods();

  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor="method">Metode forecasting</Label>
      <Select
        value={value === "" ? OTOMATIS : value}
        onValueChange={(v) => onChange(v === OTOMATIS ? "" : v)}
        disabled={isPending}
      >
        <SelectTrigger id="method">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={OTOMATIS}>Otomatis (Direkomendasikan)</SelectItem>
          {(methods ?? []).map((m) => (
            <SelectItem key={m} value={m}>
              {LABELS[m] ?? m}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
