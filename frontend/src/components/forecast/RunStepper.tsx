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
      <ol className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {steps.map((step, i) => {
          const current = step.key === active;
          return (
            <li key={step.key} className="min-w-0">
              <button
                type="button"
                aria-current={current ? "step" : undefined}
                onClick={() => onChange(step.key)}
                className={cn(
                  "flex h-full w-full items-start gap-3 rounded-lg border bg-card p-3 text-left transition-colors hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  current && "border-primary bg-primary/5 ring-1 ring-primary hover:bg-primary/10",
                  step.status === "locked" && !current && "bg-muted/30 text-muted-foreground",
                )}
              >
                <span
                  aria-hidden
                  className={cn(
                    "flex size-7 shrink-0 items-center justify-center rounded-full border text-xs font-semibold",
                    step.status === "done" && "border-success bg-success text-success-foreground",
                    step.status === "todo" && "border-primary bg-primary text-primary-foreground",
                    step.status === "locked" && "border-dashed text-muted-foreground",
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
                <span className="flex min-w-0 flex-col gap-0.5">
                  <span className="text-sm font-medium leading-tight">
                    {i + 1}. {step.label}
                  </span>
                  <span
                    className={cn(
                      "text-xs text-muted-foreground",
                      step.status === "done" && "text-success",
                      step.status === "todo" && "font-medium text-primary",
                    )}
                  >
                    {step.status === "done" ? "Selesai" : step.status === "todo" ? "Perlu tindakan" : "Terkunci"}
                  </span>
                  {/* Baris sendiri: di kartu sempit (5 kolom @1280px) hint tidak patah menempel ke status. */}
                  {step.hint && <span className="text-xs text-muted-foreground">{step.hint}</span>}
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
