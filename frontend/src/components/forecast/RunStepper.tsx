"use client";

import { Check, Lock } from "lucide-react";

import { cn } from "@/lib/utils";
import type { RunStep, RunStepKey } from "@/lib/runSteps";

// CR v3.6 §4 — stepper horizontal detail run. Status tiap langkah datang dari
// deriveRunSteps (data run). Langkah terkunci tetap bisa dibuka untuk membaca alasannya.
export function RunStepper({
  steps,
  active,
  onChange,
}: {
  steps: RunStep[];
  active: RunStepKey;
  onChange: (key: RunStepKey) => void;
}) {
  return (
    <nav aria-label="Langkah run">
      <ol className="grid gap-2 sm:grid-cols-4">
        {steps.map((step, i) => {
          const current = step.key === active;
          return (
            <li key={step.key}>
              <button
                type="button"
                aria-current={current ? "step" : undefined}
                onClick={() => onChange(step.key)}
                className={cn(
                  "flex w-full items-start gap-3 rounded-lg border p-3 text-left transition-colors hover:bg-muted/50",
                  current && "border-primary bg-muted/40",
                  step.status === "locked" && "opacity-70",
                )}
              >
                <span
                  aria-hidden
                  className={cn(
                    "flex size-7 shrink-0 items-center justify-center rounded-full border text-xs font-semibold",
                    step.status === "done" && "border-success bg-success text-success-foreground",
                    step.status === "todo" && "border-primary text-primary",
                  )}
                >
                  {step.status === "done" ? (
                    <Check className="size-4" />
                  ) : step.status === "locked" ? (
                    <Lock className="size-3.5" />
                  ) : (
                    i + 1
                  )}
                </span>
                <span className="flex min-w-0 flex-col">
                  <span className="text-sm font-medium">
                    {i + 1}. {step.label}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {step.status === "done" ? "Selesai" : step.status === "todo" ? "Perlu tindakan" : "Terkunci"}
                    {step.hint && ` · ${step.hint}`}
                  </span>
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
