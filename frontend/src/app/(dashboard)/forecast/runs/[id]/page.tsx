"use client";

import { useParams, useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { FORECAST_VIEWS, type ForecastView, RunDetail } from "@/components/forecast/RunDetail";
import type { RunStepKey } from "@/lib/runSteps";

const STEPS: RunStepKey[] = ["forecast", "select", "planning", "evaluation", "reorder"];

// CR v3.6 §1 — /forecast/runs/[id]: detail run yang bisa dibuka ulang. Baca untuk semua
// role (CR v3.5 §3.2); aksi disembunyikan per izin di dalam RunDetail. `?step=` membuka
// langkah tertentu (dipakai tautan dashboard). `?view=method|product` = tampilan langkah 1
// (CR v3.7: per metode format thesis | per produk).
function RunPageContent() {
  const { id } = useParams<{ id: string }>();
  const params = useSearchParams();
  const step = params.get("step") as RunStepKey | null;
  const view = params.get("view") as ForecastView | null;
  return (
    <RunDetail
      runId={id}
      initialStep={step && STEPS.includes(step) ? step : undefined}
      initialView={view && FORECAST_VIEWS.includes(view) ? view : undefined}
    />
  );
}

export default function ForecastRunPage() {
  return (
    <Suspense>
      <RunPageContent />
    </Suspense>
  );
}
