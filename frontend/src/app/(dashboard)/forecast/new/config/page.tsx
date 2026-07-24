"use client";

import { useState } from "react";

import { MethodSelector } from "@/components/config/MethodSelector";
import { ForecastResults } from "@/components/forecast/ForecastResults";
import { Button } from "@/components/ui/button";
import { useCreateForecastRun } from "@/hooks/useForecast";
import { useMaterials } from "@/hooks/useMaterials";

export default function ForecastConfigPage() {
  const { data: materials } = useMaterials();
  const run = useCreateForecastRun();

  const [selected, setSelected] = useState<string[]>([]);
  const [horizon, setHorizon] = useState(30);
  const [method, setMethod] = useState("");

  const toggle = (id: string) =>
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));

  const onGenerate = () => {
    run.mutate({
      material_ids: selected,
      horizon,
      method: method === "" ? null : method,
    });
  };

  return (
    <main className="container flex min-h-screen flex-col gap-6 py-16">
      <h1 className="text-2xl font-semibold">Konfigurasi Forecast</h1>

      <section className="flex flex-col gap-2">
        <h2 className="text-sm font-medium">Pilih material</h2>
        <div className="flex flex-col gap-1">
          {(materials ?? []).map((m) => (
            <label key={m.id} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={selected.includes(m.id)}
                onChange={() => toggle(m.id)}
              />
              {m.code} — {m.name}
            </label>
          ))}
          {(!materials || materials.length === 0) && (
            <p className="text-sm text-muted-foreground">Belum ada material. Tambah dulu di menu Material.</p>
          )}
        </div>
      </section>

      <div className="flex max-w-md flex-col gap-3">
        <MethodSelector value={method} onChange={setMethod} />
        <div className="flex flex-col gap-1">
          <label htmlFor="horizon" className="text-sm font-medium">
            Horizon (hari)
          </label>
          <input
            id="horizon"
            type="number"
            min={1}
            className="h-10 rounded-md border border-input bg-background px-3 text-sm"
            value={horizon}
            onChange={(e) => setHorizon(Number(e.target.value))}
          />
        </div>

        {run.isError && <p className="text-sm text-destructive">{run.error.message}</p>}

        <Button onClick={onGenerate} disabled={selected.length === 0 || run.isPending}>
          {run.isPending ? "Memproses…" : "Generate forecast"}
        </Button>
      </div>

      {run.data && <ForecastResults data={run.data} />}
    </main>
  );
}
