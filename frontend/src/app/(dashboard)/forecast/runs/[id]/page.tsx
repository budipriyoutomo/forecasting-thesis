"use client";

import { useParams, useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { RunDetail } from "@/components/forecast/RunDetail";
import type { RunStepKey } from "@/lib/runSteps";

const STEPS: RunStepKey[] = ["forecast", "select", "planning", "reorder"];

// CR v3.6 §1 — /forecast/runs/[id]: detail run yang bisa dibuka ulang. Baca untuk semua
// role (CR v3.5 §3.2); aksi disembunyikan per izin di dalam RunDetail. `?step=` membuka
// langkah tertentu (dipakai tautan dashboard).
function RunPageContent() {
  const { id } = useParams<{ id: string }>();
  const step = useSearchParams().get("step") as RunStepKey | null;
  return <RunDetail runId={id} initialStep={step && STEPS.includes(step) ? step : undefined} />;
}

export default function ForecastRunPage() {
  return (
    <Suspense>
      <RunPageContent />
    </Suspense>
  );
}
