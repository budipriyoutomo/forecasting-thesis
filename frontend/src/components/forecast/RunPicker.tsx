"use client";

import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { ForecastRunListItem } from "@/types/forecast";

export function runLabel(run: Pick<ForecastRunListItem, "run_id" | "created_at" | "created_by">): string {
  const by = run.created_by ? ` · oleh ${run.created_by}` : "";
  const id = run.run_id.slice(0, 8);
  if (!run.created_at) return `${id}${by}`;
  const d = new Date(run.created_at);
  return `${d.toLocaleString("id-ID", { dateStyle: "medium", timeStyle: "short" })} · ${id}${by}`;
}

// CR v3.6 §1/§8.3 — satu komponen pemilih run (ui/select, bukan <select> native) untuk
// semua halaman yang butuh memilih run (Kedatangan Material, dst).
export function RunPicker({
  runs,
  value,
  onChange,
  id = "run-picker",
  label = "Forecast run",
}: {
  runs: ForecastRunListItem[];
  value: string | null;
  onChange: (runId: string) => void;
  id?: string;
  label?: string;
}) {
  return (
    <div className="flex w-full max-w-md flex-col gap-1">
      <Label htmlFor={id}>{label}</Label>
      <Select value={value ?? undefined} onValueChange={onChange}>
        <SelectTrigger id={id}>
          <SelectValue placeholder="Pilih run…" />
        </SelectTrigger>
        <SelectContent>
          {runs.map((r) => (
            <SelectItem key={r.run_id} value={r.run_id}>
              {runLabel(r)}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
